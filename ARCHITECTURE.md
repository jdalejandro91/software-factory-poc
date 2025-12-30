# Software Factory PoC — Architecture Documentation

## 1. Architectural Philosophy: Screaming Architecture (DDD)
The project follows **Domain-Driven Design (DDD)** and **Clean Architecture** principles. The folder structure "screams" the intent of the application rather than the framework (FastAPI).

### Key Layers
1.  **Application Core (`application/`)**:
    *   **Domain Entities**: Pure Python objects representing business concepts (e.g., `ScaffoldingRequest`, `ScaffoldingAgent`).
    *   **Use Cases**: High-level orchestrators containing business logic (e.g., `CreateScaffoldingUseCase`).
    *   **Ports (Gateways)**: Interfaces defining contracts for external services (e.g., `VcsGateway`, `LLMGatewayPort`).
    *   **Services**: Pure domain logic services (e.g., `PromptBuilderService`, `FileParsingService`).

2.  **Infrastructure (`infrastructure/`)**:
    *   **Adapters (Providers)**: Concrete implementations of Ports (e.g., `GitLabProviderImpl` implementing `VcsGateway`).
    *   **Configuration**: Loaders and Pydantic Settings implementation.
    *   **Entrypoints**: API routers (FastAPI) and CLI scripts.
    *   **Resolution**: `ProviderResolver` (Factory) to wire adapters dynamically.

---

## 2. Core Orchestration Flow
The central workflow is managed by the `CreateScaffoldingUseCase`:

1.  **Resolver Wiring**: The `ProviderResolver` examines the configuration and instantiates the correct adapters (e.g., GitLab vs GitHub, OpenAI vs DeepSeek).
2.  **Context Retrieval**: `KnowledgeGateway` fetches relevant docs/templates.
3.  **Prompt Strategy**: `PromptBuilderService` constructs a context-aware prompt.
4.  **LLM Generation**: `LLMGatewayPort` (Composite) executes the prompt, handling fallback logic if primary models fail.
5.  **Parsing**: `FileParsingService` converts LLM response into virtual files.
6.  **Action**: `VcsGateway` applies changes (Branch/Commit/MR) to the repository.
7.  **Notification**: `TrackerGateway` updates the status in the task tracker (Jira).

---

## 3. Interfaces (Ports)
These interfaces isolate the core from external tools.

-   **`VcsGateway`**: Contracts for `create_merge_request`.
-   **`TrackerGateway`**: Contracts for `transition_task`, `comment_on_task`.
-   **`KnowledgeGateway`**: Contracts for `retrieve_context`.
-   **`LLMGatewayPort`**: Contracts for `generate_code`.

---

## 4. Configuration & Resolution
The system is strictly configuration-driven via Environment Variables.

### Provider Resolution
The `ProviderResolver` acts as the dependency injection root. It reads the `ScaffoldingAgentConfig` (loaded via `settings_loader.py`) and decides which concrete class to instantiate.

**Example**:
- If `VCS_PROVIDER=GITLAB` -> Instantiates `GitLabProviderImpl`.
- If `KNOWLEDGE_PROVIDER=FILE_SYSTEM` -> Instantiates `FileSystemKnowledgeAdapter`.

### Configuration Enums
Supported values for configuration:
-   **VCS**: `gitlab`
-   **Tracker**: `jira`
-   **LLM**: Priority list via `LLM_MODEL_PRIORITY` JSON (e.g., `openai`, `deepseek`).
