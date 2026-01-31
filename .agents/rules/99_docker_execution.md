# Ejecución Segura en Docker

El entorno de desarrollo es híbrido. El IDE corre en macOS, pero el entorno de ejecución (Runtime) está encapsulado en un contenedor Docker llamado `antigravity_session`.

## Regla Maestra de Terminal
CUALQUIER comando de terminal sugerido o ejecutado por el agente (creación de archivos, ejecución de scripts, instalaciones pip, git, etc.) DEBE ser ejecutado a través del comando `docker exec`.

### Formato de Ejecución
Siempre prefija los comandos con:
`docker exec -w /app antigravity_session <COMANDO>`

### Excepción
Solo comandos relacionados con levantar/detener el propio Docker (`docker compose...`) pueden ejecutarse en el host. Todo lo demás, estrictamente dentro del contenedor.