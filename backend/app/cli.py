"""Command line entry point: `uv run python -m app.cli <command>`."""

import os
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.config import BACKEND_DIR, get_settings
from app.db import get_engine
from app.models import AppUser, Company, UserCompany, UserRole
from app.seed import run_seed
from app.services import auth
from app.services.auth import MIN_PASSWORD_LENGTH

cli = typer.Typer(no_args_is_help=True, add_completion=False, help="Ficka administration.")


def _owner_uid(folder: Path) -> int | None:
    return folder.stat().st_uid if folder.exists() else None


def refuse_foreign_owner() -> None:
    """Refuse to run as root on a database folder owned by another user.

    In Docker the API runs as uid 1000. If the CLI ran as root (a container console
    opened as root), SQLite would create its -wal / -shm files owned by root and the
    API could no longer write to the database.
    """
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return
    folder = Path(url.database).resolve().parent
    owner = _owner_uid(folder)
    if owner is not None and owner != 0:
        typer.secho(
            f"Running as root, but {folder} belongs to uid {owner}. "
            "Run this command as that user (in Docker: the default 'ficka' user, "
            "e.g. `docker compose exec api python -m app.cli init`).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


def run_migrations() -> None:
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


def _prompt_text(label: str, value: str | None) -> str:
    while True:
        if value is None:
            value = typer.prompt(label)
        value = value.strip()
        if value:
            return value
        typer.secho(f"{label} cannot be empty.", fg=typer.colors.RED, err=True)
        value = None


def _prompt_email(value: str | None) -> str:
    while True:
        email = _prompt_text("Email", value).lower()
        local, _, domain = email.partition("@")
        if local and "." in domain and " " not in email:
            return email
        typer.secho("Please enter a valid email address.", fg=typer.colors.RED, err=True)
        value = None


def _prompt_password(value: str | None, label: str = "Password") -> str:
    while True:
        if value is None:
            value = typer.prompt(label, hide_input=True, confirmation_prompt=True)
        if len(value) >= MIN_PASSWORD_LENGTH:
            return value
        typer.secho(
            f"The password needs at least {MIN_PASSWORD_LENGTH} characters.",
            fg=typer.colors.RED,
            err=True,
        )
        value = None


@cli.command()
def init(
    company_name: str | None = typer.Option(None, help="Company name (asked if omitted)."),
    email: str | None = typer.Option(None, help="Owner email (asked if omitted)."),
    display_name: str | None = typer.Option(None, help="Owner display name (asked if omitted)."),
    password: str | None = typer.Option(
        None, help="Owner password (asked, hidden, if omitted; avoid it in shared shells)."
    ),
) -> None:
    """Run the migrations, create the company and its owner, then seed."""
    refuse_foreign_owner()
    run_migrations()

    engine = get_engine()
    with Session(engine) as session:
        if session.exec(select(Company.id)).first() is not None:
            typer.secho(
                "A company already exists: init has already been run.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    company_name = _prompt_text("Company name", company_name)
    email = _prompt_email(email)
    display_name = _prompt_text("Display name", display_name)
    password = _prompt_password(password)
    password_hash = auth.hash_password(password)  # argon2id

    with Session(engine) as session:
        # VAT country first: company.country_code references it.
        run_seed(session)
        company = Company(name=company_name)
        user = AppUser(email=email, password_hash=password_hash, display_name=display_name)
        session.add(company)
        session.add(user)
        session.flush()
        assert company.id is not None and user.id is not None
        session.add(UserCompany(user_id=user.id, company_id=company.id, role=UserRole.OWNER))
        session.commit()
        result = run_seed(session)

    typer.secho(
        f"Created company '{company_name}' with owner {email} "
        f"({result.categories} categories seeded).",
        fg=typer.colors.GREEN,
    )


@cli.command("reset-password")
def reset_password(
    email: str | None = typer.Option(None, help="Email of the account (asked if omitted)."),
    password: str | None = typer.Option(
        None, hidden=True, help="New password (asked, hidden, if omitted)."
    ),
) -> None:
    """Set a new password for an account and sign out all its sessions."""
    refuse_foreign_owner()
    email = _prompt_email(email)
    with Session(get_engine()) as session:
        user = session.exec(select(AppUser).where(AppUser.email == email)).first()
        if user is None:
            typer.secho(f"No account with the email {email}.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        new_password = _prompt_password(password, "New password")
        auth.set_password(session, user, new_password)
        assert user.id is not None
        signed_out = auth.delete_all_sessions(session, user.id)

    typer.secho(
        f"Password changed for {email}; {signed_out} session(s) signed out.",
        fg=typer.colors.GREEN,
    )


@cli.command()
def seed() -> None:
    """Re-run the idempotent seed (VAT rates, company settings, default categories)."""
    refuse_foreign_owner()
    with Session(get_engine()) as session:
        result = run_seed(session)
    if result.total:
        typer.echo(
            f"Seeded {result.countries} countries, {result.rates} VAT rates, "
            f"{result.settings} settings rows, {result.categories} categories."
        )
    else:
        typer.echo("Nothing to seed: everything is already in place.")


if __name__ == "__main__":
    cli()
