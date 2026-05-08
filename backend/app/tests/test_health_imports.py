def test_app_settings_imports():
    from config.settings import settings
    assert settings.JWT_ALGORITHM == "HS256"


def test_auth_router_imports():
    from api.auth_router import router
    assert router.prefix == "/api/auth"
