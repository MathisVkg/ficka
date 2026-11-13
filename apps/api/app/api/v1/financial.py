from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Category
from app.schemas.financial import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    EntryCreate,
    EntryOut,
    EntryPage,
    EntryStatus,
    EntryType,
    EntryUpdate,
)
from app.services import financial as service

router = APIRouter()
DB = Annotated[Session, Depends(get_session)]


def entry_router(prefix: str, kind: str) -> APIRouter:
    routes = APIRouter(prefix=prefix, tags=[kind])

    @routes.get("", response_model=EntryPage)
    def list_all(
        session: DB,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        date_from: date | None = None,
        date_to: date | None = None,
        status: EntryStatus | None = None,
        category_id: UUID | None = None,
        search: Annotated[str | None, Query(max_length=200)] = None,
        sort: Literal["date", "amount", "created_at"] = "date",
        direction: Literal["asc", "desc"] = "desc",
    ):
        return service.list_entries(
            session,
            kind,
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            status=status,
            category_id=category_id,
            search=search,
            sort=sort,
            direction=direction,
        )

    @routes.post("", response_model=EntryOut, status_code=201)
    def create(data: EntryCreate, session: DB):
        return service.create_entry(session, kind, data)

    @routes.get("/{entry_id}", response_model=EntryOut)
    def detail(entry_id: UUID, session: DB):
        return service.get_entry(session, kind, entry_id)

    @routes.patch("/{entry_id}", response_model=EntryOut)
    def update(entry_id: UUID, data: EntryUpdate, session: DB):
        return service.update_entry(session, kind, entry_id, data)

    @routes.delete("/{entry_id}", status_code=204)
    def delete(entry_id: UUID, session: DB):
        service.delete_entry(session, kind, entry_id)
        return Response(status_code=204)

    return routes


router.include_router(entry_router("/income", "income"))
router.include_router(entry_router("/expenses", "expense"))


@router.get("/categories", response_model=list[CategoryOut], tags=["categories"])
def categories(session: DB, type: EntryType | None = None, active: bool | None = None):
    query = select(Category)
    if type is not None:
        query = query.where(Category.type == type)
    if active is not None:
        query = query.where(Category.active == active)
    return session.scalars(query.order_by(Category.type, Category.name_key)).all()


@router.post("/categories", response_model=CategoryOut, status_code=201, tags=["categories"])
def create_category(data: CategoryCreate, session: DB):
    return service.create_category(session, data)


@router.patch("/categories/{category_id}", response_model=CategoryOut, tags=["categories"])
def update_category(category_id: UUID, data: CategoryUpdate, session: DB):
    return service.update_category(session, category_id, data)
