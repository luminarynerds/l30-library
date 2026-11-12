from app.services.google_books_fetcher import GoogleBooksFetcher


def test_explicit_api_key_wins(monkeypatch):
    f = GoogleBooksFetcher(api_key="explicit-key")
    assert f.api_key == "explicit-key"


def test_api_key_defaults_from_settings(monkeypatch):
    import app.core.config as config
    config.get_settings.cache_clear()
    monkeypatch.setenv("GOOGLE_BOOKS_API_KEY", "from-env-key")
    config.get_settings.cache_clear()
    f = GoogleBooksFetcher()
    assert f.api_key == "from-env-key"
    config.get_settings.cache_clear()


def test_no_key_is_none_when_unset(monkeypatch):
    import app.core.config as config
    monkeypatch.delenv("GOOGLE_BOOKS_API_KEY", raising=False)
    config.get_settings.cache_clear()
    f = GoogleBooksFetcher()
    assert f.api_key is None
    config.get_settings.cache_clear()
