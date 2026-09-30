from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from app.config import settings
from app.db.models import Base

config = context.config

if not config.get_main_option("sqlalchemy.url"):
    # alembic runs synchronously — convert the app's asyncpg URL to pg8000
    db_url = make_url(settings.DATABASE_URL)
    query = dict(db_url.query)
    had_ssl = "ssl" in query or "sslmode" in query
    query.pop("ssl", None)
    query.pop("sslmode", None)
    if had_ssl:
        query["ssl_context"] = "True"
    sync_url = db_url.set(drivername="postgresql+pg8000", query=query)
    # configparser treats % as interpolation syntax; escape % as %%
    escaped_url = sync_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", escaped_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
