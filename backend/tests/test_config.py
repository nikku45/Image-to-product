from app.config import Settings


def test_default_settings():
    """Verify default settings values and computed properties."""
    settings = Settings(_env_file=None)
    assert settings.app_env in ["development", "testing"]
    assert settings.backend_port == 8000
    assert settings.max_upload_size_mb == 10
    assert settings.max_upload_size_bytes == 10 * 1024 * 1024
    assert settings.gemini_model == "gemini-3.8-flash"
    assert "http://localhost:3000" in settings.cors_origins


def test_cors_origins_parsing_from_string(monkeypatch):
    """Verify comma-separated CORS origins from the environment become a list."""
    monkeypatch.setenv("CORS_ORIGINS", "https://shop.vercel.app, https://preview.vercel.app")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["https://shop.vercel.app", "https://preview.vercel.app"]


def test_cors_origins_parsing_from_init_value():
    """Verify comma-separated CORS values passed to Settings become a list."""
    settings = Settings(CORS_ORIGINS="http://example.com, https://app.example.com")
    assert settings.cors_origins == ["http://example.com", "https://app.example.com"]
