import json

from software_factory_poc.infrastructure.tools.tracker.jira.mappers import JiraPanelFactory

# 1. Scaffolding Case (Existing Branch)
scaff_data = {
    "type": "scaffolding_exists",
    "title": "⚠️ El Scaffolding ya existe",
    "summary": "Rama detectada...",
    "links": {"🔗 Ver Merge Request Existing": "https://gitlab.com/mr/37"},
}

# 2. Code Review Case
review_data = {
    "type": "code_review_success",
    "title": "Code Review Finalizado",
    "summary": "Comentarios publicados.",
    "links": {"🔗 Ver Merge Request": "https://gitlab.com/mr/44"},
}

print("\n--- Scaffolding Output ---")
print(json.dumps(JiraPanelFactory.create_payload(scaff_data), indent=2))

print("\n--- Code Review Output ---")
print(json.dumps(JiraPanelFactory.create_payload(review_data), indent=2))
