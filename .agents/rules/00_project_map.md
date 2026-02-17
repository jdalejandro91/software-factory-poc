# 00_project_map.md — The BrahMAS Package Structure (2026 MAS Standard)

> **Core Tech Stack**: Pure Python 3.12, Clean Architecture, DDD, MCP (Model Context Protocol), LiteLLM, Pydantic.

## Directory Map (Screaming Architecture)
Dependencies ONLY point inwards: `infrastructure` -> `core/application` -> `core/domain`.

```text
software_factory/                              # Raíz del proyecto. Agrupa todas las capas bajo un mismo bounded context.
├── core/                                      # 🟢 NÚCLEO LIMPIO: dominio + aplicación. No depende de frameworks ni I/O concreto.
│   ├── domain/                                # MODELO DEL NEGOCIO: invariantes, VOs, entidades y agregados. Sin APIs/DBs.
│   │   ├── mission/                           # Subdominio de intención: Mission (AR), Intent/Constraints/ContextRefs/Status.
│   │   ├── run/                               # Ejecución durable: Run (AR), RunStep, estados, idempotency, artefactos.
│   │   ├── skill/                             # Catálogo/versionado/contratos/políticas de skills.
│   │   ├── quality/                           # Guardrails de calidad: CodeReviewReport (VO), severidades, comentarios.
│   │   ├── delivery/                          # Entrega/cambios: CommitIntent (VO), RepoRef, BranchName, FileContent, MRRef.
│   │   ├── work_tracking/                     # Tracking: TaskRef + snapshots de lectura (sin acoplarse a Jira u otra tool).
│   │   └── shared/                            # Primitivas transversales: correlation ids, errores tipados, tiempo/clock.
│   │
│   └── application/                           # 🔵 ORQUESTACIÓN Y CASOS DE USO: orquesta dominio + puertos.
│       ├── orchestration/                     # Servicios top-level: crean Missions, inician/reanudan Runs, aplican macro-policies.
│       ├── agents/                            # AGENTIC FLOW: Roles/orquestadores. Deciden skills, controlan flujo, act loops.
│       ├── skills/                            # DETERMINISTIC FLOW: Unidades reutilizables que producen VOs usando puertos.
│       │   ├── scaffold/                      # Plan/generate/apply.
│       │   └── review/                        # Fetch diff/analyze/publish.
│       ├── policies/                          # Políticas aplicadas: quality gates, budgets, approvals, naming.
│       └── tools/                             # INTERFACES HACIA AFUERA: LLM, VCS, tracker, docs
│
└── infrastructure/                            # 🔴 MUNDO "SUCIO": implementaciones concretas, frameworks, I/O, DB, HTTP, MCP.
    ├── entrypoints/                           # DRIVERS INBOUND: API/CLI. Reciben requests, validan, y llaman a aplicación.
    │   ├── api/                               # HTTP/webhooks/controllers: traduce request→input, invoca MissionService.
    │   └── mcp_server/                        # MCP Server: Expone endpoints para clientes MCP.
    │
    ├── tools/                                 # TOOLS OUTBOUND: Integraciones para side-effects (LLM/VCS/Tracker/Docs/CI).
    │   ├── llm/                               # Providers LLM (LiteLLM) + validación schema, retries.
    │   │   └── config/                        # litellm config files.
    │   ├── vcs/                               # MCP Clients (GitLab/Bitbucket/GitHub). Enrutamiento dinámico (Coexistencia).
    │   │   └── gitlab/                        # GitLab tool driver.
    │   │       └── config/                    # vsc config files.
    │   ├── tracker/                           # MCP Clients (Jira/AzureDevOps). Enrutamiento dinámico.
    │   │   └── jira/                          # Jira tool driver.
    │   │       └── config/                    # Jira config files.
    │   └── docs/                              # MCP Clients (Confluence/Notion).
    │       └── confluence/                    # Confluence tool driver.
    │           └── config/                    # Confluence config files.
    │
    ├── persistence/                           # PERSISTENCIA CONCRETA: DBs y storage.
    │   ├── run_store/                         # Almacén durable de Runs/steps (Mongo/Postgres/etc.).
    │   ├── artifact_store/                    # Almacén de artefactos/evidencias (S3/FS/etc.).
    │   └── skill_store/                       # Almacén/registro versionado de skills (file/db).
    │
    └── adapters/                              # ADAPTADORES DE TRANSFORMACIÓN.
        └── mappers/                           # Mappers específicos (MCP JSON ↔ Domain VOs) y normalización. Aisla la suciedad.