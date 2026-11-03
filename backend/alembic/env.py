from sqlalchemy import create_engine, pool

from alembic import context
from app import models  # noqa: F401
from app.core.config import settings
from app.core.db import Base

config = context.config
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    return name != "spatial_ref_sys"


def run_migrations_offline() -> None:
    context.configure(
        url=settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        settings().database_url,
        poolclass=pool.NullPool,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
    )
    with connectable.connect() as connection:
        connection.exec_driver_sql("SET search_path TO public")
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
