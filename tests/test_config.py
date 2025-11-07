from config import settings


def test_get_llm_settings_uses_defaults(monkeypatch):
    monkeypatch.setattr(settings, "litellm_image_model", None, raising=False)
    monkeypatch.setattr(settings, "litellm_image_api_key", None, raising=False)
    monkeypatch.setattr(settings, "litellm_image_api_base", None, raising=False)
    monkeypatch.setattr(settings, "litellm_image_extra_params", {}, raising=False)

    monkeypatch.setattr(settings, "litellm_default_model", "default-model", raising=False)
    monkeypatch.setattr(settings, "litellm_default_api_key", "default-key", raising=False)
    monkeypatch.setattr(settings, "litellm_default_api_base", "https://default", raising=False)
    monkeypatch.setattr(settings, "litellm_default_extra_params", {"foo": "bar"}, raising=False)

    llm_settings = settings.get_llm_settings("image")

    assert llm_settings.model == "default-model"
    assert llm_settings.api_key == "default-key"
    assert llm_settings.api_base == "https://default"
    assert llm_settings.extra_params == {"foo": "bar"}


def test_get_llm_settings_merges_domain(monkeypatch):
    monkeypatch.setattr(settings, "litellm_docs_model", "docs-model", raising=False)
    monkeypatch.setattr(settings, "litellm_docs_api_key", "docs-key", raising=False)
    monkeypatch.setattr(settings, "litellm_docs_api_base", "https://docs", raising=False)
    monkeypatch.setattr(settings, "litellm_default_extra_params", {"foo": "bar"}, raising=False)
    monkeypatch.setattr(settings, "litellm_docs_extra_params", {"docs": "value"}, raising=False)

    llm_settings = settings.get_llm_settings("docs")

    assert llm_settings.model == "docs-model"
    assert llm_settings.api_key == "docs-key"
    assert llm_settings.api_base == "https://docs"
    assert llm_settings.extra_params == {"foo": "bar", "docs": "value"}
