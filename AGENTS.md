# Reglas para Agentes IDE

Este documento define las pautas de interacción para agentes de IA que trabajan en este repositorio.

## Navegación
- **Siempre** usa rutas absolutas al leer o escribir archivos.
- Antes de editar un archivo, lee su contenido para entender el contexto.
- Usa `ls -R` o herramientas de búsqueda para ubicar archivos si no conoces la estructura exacta.

## Convenciones
- **Idioma**: El código y los comentarios deben estar en Inglés (estándar de la industria), pero la documentación de alto nivel (como este archivo) puede estar en Español si el usuario lo prefiere. *Nota: Mantendremos el código en inglés.*
- **Estilo**: Sigue PEP 8. Usa `ruff` para formateo.
- **Tipado**: Usa type hints de Python en todas las firmas de funciones y métodos públicos.

## Límites
- **No** modifiques archivos fuera del directorio de trabajo actual sin permiso explícito.
- **No** "inventes" dependencias. Si necesitas una librería nueva, agrégala explícitamente a `pyproject.toml` y notifica al usuario.
- **No** borres código sin entender qué hace (usa búsqueda de referencias).

## Do's and Don'ts

### Do
- Crear tests para nuevo código.
- Documentar funciones complejas con docstrings.
- Pedir clarificación si una tarea es ambigua.

### Don't
- Dejar código comentado "por si acaso" (usa git para historial).
- Crear archivos temporales sin borrarlos (o agregarlos a .gitignore).
- Cambiar la configuración del proyecto (linters, build) sin una buena razón.
