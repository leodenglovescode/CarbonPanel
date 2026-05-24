import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Base.metadata is populated
from app.database import Base  # noqa: E402
from app.config import settings  # noqa: E402
import app.models.user  # noqa: E402, F401
import app.models.site  # noqa: E402, F401
import app.models.app_label  # noqa: E402, F401
import app.models.webhook  # noqa: E402, F401
import app.models.device  # noqa: E402, F401
import app.models.bookmark  # noqa: E402, F401
import app.models.dashboard_layout  # noqa: E402, F401
import app.models.webauthn_credential  # noqa: E402, F401
import app.models.user_preferences  # noqa: E402, F401

# Override alembic.ini's sqlalchemy.url with the value from settings so that
# DATABASE_URL in the environment is always used (e.g. production vs local dev).
config.set_main_option("sqlalchemy.url", str(settings.database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
