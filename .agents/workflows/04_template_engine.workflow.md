# 04_template_engine.workflow.md — Template engine determinista (manifest + expected_paths)

## Objetivo
Implementar:
- template_registry (template_id -> folder)
- manifest model (expected_paths, supported_vars, template_version)
- renderer determinista (Jinja -> files_map[path]=content)
- validación expected_paths

## Entradas
- template_id
- vars (dict)
- template_catalog local

## Archivos a crear/modificar
- src/software_factory_poc/templates/template_registry_service.py
- src/software_factory_poc/templates/template_manifest_model.py
- src/software_factory_poc/templates/template_renderer_service.py
- src/software_factory_poc/templates/template_file_loader_service.py
- src/software_factory_poc/templates/template_catalog/corp_nodejs_api/*
- tests/test_template_renderer.py

## Pasos
1) Definir estructura de template:
   - template_manifest.yaml
   - archivos .j2
2) Cargar manifest y validar fields.
3) Cargar archivos .j2 del folder.
4) Renderizar con Jinja2 usando vars (default safe).
5) Construir files_map[path]=content (paths estables).
6) Validar expected_paths: deben existir en files_map.

## Criterios de aceptación
- Dada una entrada fija, render produce mismos archivos y contenido
- expected_paths falla con mensaje claro si falta algo
- Test cubre caso normal y caso falta expected_path

## Comandos de validación
- uv run sf-poc-test
