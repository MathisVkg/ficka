"""Categories: per company, per direction, ordered by `position`.

Every function takes `company_id` first; a category of another company behaves as if it
didn't exist (NotFound).
"""

from dataclasses import dataclass

from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.errors import Conflict, NotFound, ValidationFailed
from app.models import Category, Counterparty, Direction, Entry, RecurringTemplate
from app.models.base import utc_now


@dataclass(frozen=True)
class CategoryUsage:
    entries: int
    templates: int
    counterparties: int

    @property
    def total(self) -> int:
        return self.entries + self.templates + self.counterparties


def get_category(session: Session, company_id: int, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None or category.company_id != company_id:
        raise NotFound("This category doesn't exist.")
    return category


def usage_of(session: Session, category_id: int) -> CategoryUsage:
    entries = session.exec(
        select(func.count()).select_from(Entry).where(Entry.category_id == category_id)
    ).one()
    templates = session.exec(
        select(func.count())
        .select_from(RecurringTemplate)
        .where(RecurringTemplate.category_id == category_id)
    ).one()
    counterparties = session.exec(
        select(func.count())
        .select_from(Counterparty)
        .where(Counterparty.default_category_id == category_id)
    ).one()
    return CategoryUsage(entries, templates, counterparties)


def list_categories(
    session: Session, company_id: int, direction: Direction | None = None
) -> list[tuple[Category, CategoryUsage]]:
    entries = (
        select(func.count())
        .select_from(Entry)
        .where(Entry.category_id == Category.id)
        .correlate(Category)
        .scalar_subquery()
    )
    templates = (
        select(func.count())
        .select_from(RecurringTemplate)
        .where(RecurringTemplate.category_id == Category.id)
        .correlate(Category)
        .scalar_subquery()
    )
    counterparties = (
        select(func.count())
        .select_from(Counterparty)
        .where(Counterparty.default_category_id == Category.id)
        .correlate(Category)
        .scalar_subquery()
    )
    query = select(Category, entries, templates, counterparties).where(
        Category.company_id == company_id
    )
    if direction is not None:
        query = query.where(Category.direction == direction)
    query = query.order_by(col(Category.direction), col(Category.position), col(Category.id))
    return [(category, CategoryUsage(e, t, c)) for category, e, t, c in session.exec(query).all()]


def _check_name_free(
    session: Session, company_id: int, direction: Direction, name: str, exclude_id: int | None
) -> None:
    query = select(Category.id).where(
        Category.company_id == company_id,
        Category.direction == direction,
        func.lower(Category.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(Category.id != exclude_id)
    if session.exec(query).first() is not None:
        raise Conflict(
            f"A {direction.value} category named “{name}” already exists.",
            fields={"name": "This name is already used."},
        )


def _clean_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationFailed("Enter a name.", fields={"name": "Enter a name."})
    return name


def create_category(
    session: Session,
    company_id: int,
    *,
    direction: Direction,
    name: str,
    default_vat_rate_bp: int | None,
    known_rates: set[int],
) -> Category:
    name = _clean_name(name)
    _check_vat_default(default_vat_rate_bp, known_rates)
    _check_name_free(session, company_id, direction, name, None)
    last = session.exec(
        select(func.max(Category.position)).where(
            Category.company_id == company_id, Category.direction == direction
        )
    ).one()
    category = Category(
        company_id=company_id,
        direction=direction,
        name=name,
        default_vat_rate_bp=default_vat_rate_bp,
        position=(last + 1) if last is not None else 0,
    )
    session.add(category)
    _commit_unique(session, name)
    session.refresh(category)
    return category


def _check_vat_default(rate_bp: int | None, known_rates: set[int]) -> None:
    if rate_bp is not None and rate_bp not in known_rates:
        raise ValidationFailed(
            "This VAT rate doesn't exist.",
            fields={"default_vat_rate_bp": "Choose one of the VAT rates, or no VAT."},
        )


def _commit_unique(session: Session, name: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict(
            f"A category named “{name}” already exists.",
            fields={"name": "This name is already used."},
        ) from exc


def update_category(
    session: Session,
    company_id: int,
    category_id: int,
    changes: dict,
    known_rates: set[int],
) -> Category:
    category = get_category(session, company_id, category_id)
    direction = changes.get("direction", category.direction)
    if direction != category.direction and usage_of(session, category_id).total > 0:
        raise Conflict(
            "This category is in use, so its direction can't change.",
            fields={"direction": "The category is in use."},
        )
    name = _clean_name(changes["name"]) if "name" in changes else category.name
    if "default_vat_rate_bp" in changes:
        _check_vat_default(changes["default_vat_rate_bp"], known_rates)
        category.default_vat_rate_bp = changes["default_vat_rate_bp"]
    if name != category.name or direction != category.direction:
        _check_name_free(session, company_id, direction, name, category_id)
    category.name = name
    category.direction = direction
    if "position" in changes:
        category.position = changes["position"]
    category.updated_at = utc_now()
    session.add(category)
    _commit_unique(session, name)
    session.refresh(category)
    return category


def reorder_categories(
    session: Session, company_id: int, direction: Direction, ids: list[int]
) -> None:
    existing = set(
        session.exec(
            select(Category.id).where(
                Category.company_id == company_id, Category.direction == direction
            )
        ).all()
    )
    if len(ids) != len(set(ids)) or set(ids) != existing:
        raise ValidationFailed(
            "Send every category of this direction exactly once.",
            fields={"ids": "Send every category of this direction exactly once."},
        )
    now = utc_now()
    for position, category_id in enumerate(ids):
        session.exec(
            update(Category)
            .where(col(Category.id) == category_id)
            .values(position=position, updated_at=now)
        )
    session.commit()


def delete_category(
    session: Session, company_id: int, category_id: int, reassign_to: int | None
) -> CategoryUsage:
    """Delete a category; a used one needs `reassign_to` (same direction, another category)."""
    category = get_category(session, company_id, category_id)
    usage = usage_of(session, category_id)
    if usage.total > 0:
        if reassign_to is None:
            raise Conflict(
                f"This category is used by {usage.entries} entries, {usage.templates} recurring "
                f"templates and {usage.counterparties} counterparties. Move them first.",
                extra={
                    "usage": {
                        "entries": usage.entries,
                        "templates": usage.templates,
                        "counterparties": usage.counterparties,
                    }
                },
            )
        if reassign_to == category_id:
            raise ValidationFailed(
                "Choose another category.", fields={"reassign_to": "Choose another category."}
            )
        try:
            target = get_category(session, company_id, reassign_to)
        except NotFound as exc:
            raise ValidationFailed(
                "This category doesn't exist.", fields={"reassign_to": "Choose a category."}
            ) from exc
        if target.direction != category.direction:
            raise ValidationFailed(
                "The new category must have the same direction.",
                fields={"reassign_to": "Choose a category of the same direction."},
            )
        session.exec(
            update(Entry).where(col(Entry.category_id) == category_id).values(category_id=target.id)
        )
        session.exec(
            update(RecurringTemplate)
            .where(col(RecurringTemplate.category_id) == category_id)
            .values(category_id=target.id)
        )
        session.exec(
            update(Counterparty)
            .where(col(Counterparty.default_category_id) == category_id)
            .values(default_category_id=target.id)
        )
    session.delete(category)
    session.commit()
    return usage
