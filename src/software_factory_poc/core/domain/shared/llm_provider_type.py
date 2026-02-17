from enum import StrEnum, auto


class LlmProviderType(StrEnum):
    OPENAI = auto()
    DEEPSEEK = auto()
    ANTHROPIC = auto()
    GEMINI = auto()
    GATEWAY = auto()

    @property
    def supported_models(self) -> list[str]:
        return SUPPORTED_MODELS_BY_PROVIDER.get(self, [])


SUPPORTED_MODELS_BY_PROVIDER: dict[LlmProviderType, list[str]] = {
    LlmProviderType.OPENAI: ["gpt-4-turbo", "gpt-4o", "gpt-o4-mini"],
    LlmProviderType.DEEPSEEK: ["deepseek-coder", "deepseek-chat"],
    LlmProviderType.ANTHROPIC: ["claude-3-5-sonnet"],
    LlmProviderType.GEMINI: ["gemini-1.5-pro", "gemini-3-flash-preview"],
}
