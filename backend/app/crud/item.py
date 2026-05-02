import uuid
from collections.abc import Sequence

from sqlmodel import Session, col, func, select

from app.models import Item
from app.schemas import ItemCreate, ItemUpdate


def count_items(*, session: Session, owner_id: uuid.UUID | None = None) -> int:
    statement = select(func.count()).select_from(Item)
    if owner_id is not None:
        statement = statement.where(Item.owner_id == owner_id)
    return session.exec(statement).one()


def get_items(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: uuid.UUID | None = None,
) -> Sequence[Item]:
    statement = select(Item)
    if owner_id is not None:
        statement = statement.where(Item.owner_id == owner_id)
    statement = (
        statement.order_by(col(Item.created_at).desc()).offset(skip).limit(limit)
    )
    return session.exec(statement).all()


def get_item(*, session: Session, item_id: uuid.UUID) -> Item | None:
    return session.get(Item, item_id)


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Item:
    update_dict = item_in.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(update_dict)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_item(*, session: Session, db_item: Item) -> None:
    session.delete(db_item)
    session.commit()
