from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    pool_recycle=300,
)
# Ingestion is the only async DB consumer and runs hours apart. Keeping its
# connection pooled just gives managed Postgres providers time to close it
# before the next run. A fresh connection per ingest is cheap and removes that
# stale-connection failure mode entirely.
async_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    poolclass=NullPool,
)


# make sure all SQLModel table models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the table models are imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
