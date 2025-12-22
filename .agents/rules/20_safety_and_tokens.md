# 20_safety_and_tokens.md — Seguridad, secretos y límites

## 1) Secretos (regla de hierro)
- Nunca hardcodear tokens (JIRA_TOKEN, GITLAB_TOKEN, etc.).
- Nunca imprimir tokens en logs.
- Nunca incluir tokens en comentarios Jira.
- Nunca commitear .env (solo .env.example).

## 2) Redacción (obligatoria en logs)
- Antes de loggear headers/responses, pasar por:
  - src/software_factory_poc/observability/redaction_service.py
- Redactar al menos:
  - Authorization, Bearer, Private-Token, cookies, refresh tokens, session ids.

## 3) Operaciones peligrosas (no permitidas en PoC)
- No mergear MRs.
- No commitear directamente a main.
- No borrar ramas.
- No ejecutar comandos en el host fuera del repo.

## 4) Archivos del sistema / contenedor (prohibido)
- No tocar /etc, /usr, /bin, ~/.ssh, etc.
- Solo escribir dentro del repo y runtime_data/.

## 5) Datos sensibles en Jira
- Si el issue contiene información sensible, el comentario debe:
  - ser minimalista
  - no copiar texto sensible
  - solo incluir el MR link y un resumen “safe”
