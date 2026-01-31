from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver


def test_resolve_model_success():
    # Setup
    resolver = ProviderResolver()
    
    # Execute
    # Assuming the method allows passing a string or has a default behavior we want to test.
    # Based on typical usage: resolve("gpt-4") -> ModelId(OPENAI, "gpt-4")
    model_id = resolver.resolve("gpt-4")
    
    # Verify
    assert model_id.name == "gpt-4"
    assert model_id.provider == LlmProviderType.OPENAI

def test_resolve_model_anthropic():
    resolver = ProviderResolver()
    model_id = resolver.resolve("claude-3-opus")
    
    assert model_id.name == "claude-3-opus"
    assert model_id.provider == LlmProviderType.ANTHROPIC

def test_resolve_unknown_defaults_to_openai():
    resolver = ProviderResolver()
    model_id = resolver.resolve("unknown-model")
    
    # Based on typical robust implementation
    assert model_id.provider == LlmProviderType.OPENAI
