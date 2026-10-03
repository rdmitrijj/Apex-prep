from app.core.db import normalize_db_url


def test_neon_direct_url() -> None:
    url, args = normalize_db_url(
        "postgresql://u:p@ep-x-123.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+asyncpg://u:p@ep-x-123.eu-central-1.aws.neon.tech/neondb"
    assert args == {"ssl": "require"}


def test_neon_pooled_url_disables_statement_caches() -> None:
    url, args = normalize_db_url(
        "postgres://u:p@ep-x-123-pooler.eu-central-1.aws.neon.tech/db?sslmode=require"
    )
    assert (
        url
        == "postgresql+asyncpg://u:p@ep-x-123-pooler.eu-central-1.aws.neon.tech/db?prepared_statement_cache_size=0"
    )
    assert args == {"ssl": "require", "statement_cache_size": 0}


def test_local_url_untouched_except_driver() -> None:
    assert normalize_db_url("postgresql://apex:apex@localhost:5432/apex") == (
        "postgresql+asyncpg://apex:apex@localhost:5432/apex",
        {},
    )
