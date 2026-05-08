def test_knowledge_settings_imports():
    from config.settings import settings
    assert settings.CHUNK_OVERLAP == 200


def test_schema_imports():
    from schemas.schema import QueryRequest
    assert QueryRequest(question="x").question == "x"
