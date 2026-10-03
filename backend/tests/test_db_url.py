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


def test_blank_env_values_mean_unset(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import pytest

    from app.core.config import DEV_SECRET, Settings

    monkeypatch.setenv("SECRET_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("RENDER", "false")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.secret_key == DEV_SECRET and s.anthropic_api_key is None
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]
