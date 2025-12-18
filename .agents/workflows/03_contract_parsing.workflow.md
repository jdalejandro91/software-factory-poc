# 03_contract_parsing.workflow.md — Parser + validación del contract (Pydantic)

## Objetivo
Extraer el bloque delimitado de la descripción y validarlo contra ScaffoldingContractModel.

## Entradas
- issue_description (string)
- delimitadores exactos definidos en 30_mvp_flow_contract.md

## Archivos a crear/modificar
- src/software_factory_poc/contracts/scaffolding_contract_model.py
- src/software_factory_poc/contracts/scaffolding_contract_parser_service.py
- tests/test_scaffolding_contract_parser.py
- tests/test_scaffolding_contract_validation.py

## Pasos
1) Implementar parser robusto:
   - encuentra bloque delimitado
   - soporta YAML (recomendado) y opcional JSON
2) Implementar modelo Pydantic:
   - required fields
   - enums básicos
   - validaciones (template_id non-empty, project_id positive, etc.)
3) Tests:
   - description sin bloque -> error claro
   - delimitadores mal escritos -> error claro
   - YAML inválido -> error claro
   - contract válido -> model correcto

## Criterios de aceptación
- Parser y validación cubren casos borde
- Errores devueltos son aptos para comentar en Jira (safe)
- Tests pasan

## Comandos de validación
- uv run sf-poc-test
