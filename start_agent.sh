#!/bin/bash

# --- CONFIGURACIÓN ---
PORT=8000
SESSION_NAME="antigravity_session"
SERVICE_NAME="app"

# ==========================================
# FASE 0: VERIFICACIÓN Y AUTO-ARRANQUE DE DOCKER
# ==========================================

# Función para verificar si Docker respponde
check_docker() {
    docker info > /dev/null 2>&1
}

if ! check_docker; then
    echo "🐳 Docker está apagado. Iniciando Docker Desktop..."
    
    # Intentamos abrir la aplicación en MacOS
    open -a Docker
    
    echo "⏳ Esperando a que el motor de Docker arranque (esto puede tomar unos segundos)..."
    
    # Bucle de espera (Timeout de 60 segundos aprox)
    MAX_RETRIES=30
    COUNT=0
    
    while ! check_docker; do
        sleep 2
        echo -n "." # Efecto de carga visual
        ((COUNT++))
        
        if [ $COUNT -ge $MAX_RETRIES ]; then
            echo ""
            echo "❌ Error: Docker tardó demasiado en iniciar."
            echo "   Por favor inicia 'Docker' manualmente y vuelve a intentar."
            exit 1
        fi
    done
    echo ""
    echo "✅ Docker está listo y respondiendo."
else
    echo "✅ Docker ya estaba corriendo."
fi

# ==========================================
# FASE 1: LIMPIEZA DE ZONA (Reset)
# ==========================================
echo "🧹 Limpiando entorno anterior..."

# 1. Eliminar contenedor viejo si existe
if [ "$(docker ps -aq -f name=$SESSION_NAME)" ]; then
    docker rm -f $SESSION_NAME > /dev/null 2>&1
fi

# 2. Liberar el puerto 8000 en la Mac (Force Kill)
PID=$(lsof -ti :$PORT)
if [ ! -z "$PID" ]; then
  kill -9 $PID
  echo "🔌 Puerto $PORT liberado."
fi

# ==========================================
# FASE 2: DESPEGUE
# ==========================================
echo "🚀 Levantando Agente Antigravity..."

# 3. Iniciar en background (-d)
docker compose run -d --name $SESSION_NAME --rm --service-ports $SERVICE_NAME \
    uvicorn src.software_factory_poc.main:app --host 0.0.0.0 --port $PORT --reload > /dev/null

# Espera técnica para que uvicorn inicie
sleep 2

# 4. Verificación final
if [ "$(docker ps -q -f name=$SESSION_NAME)" ]; then
    echo "-----------------------------------------------------------"
    echo "🤖 SISTEMA ONLINE."
    echo "   - Servidor: http://localhost:$PORT"
    echo "   - Entorno:  Aislado (Docker)"
    echo "-----------------------------------------------------------"
    echo "🔌 Conectando tu terminal a la jaula..."
    
    # 5. Conexión automática interactiva
    docker exec -it $SESSION_NAME /bin/bash
    
    # Al salir...
    echo "🛑 Apagando todo..."
    docker stop $SESSION_NAME > /dev/null 2>&1
else
    echo "❌ Error: El contenedor falló al iniciar. Revisa 'docker logs $SESSION_NAME'"
    exit 1
fi

###
#Estás operando desde un entorno host (macOS) pero DEBES ejecutar todo el trabajo dentro del contenedor Docker activo llamado antigravity_session.

#REGLA: Nunca ejecutes comandos directamente en la shell. ACCIÓN: Para cada comando de terminal que necesites correr, debes envolverlo usando docker exec.

#Ejemplo:

#En vez de: ls -la

#Ejecuta: docker exec antigravity_session ls -la

#En vez de: python main.py

#Ejecuta: docker exec antigravity_session python main.py

#¿Entendido? Confirma ejecutando uname -a usando esta nueva regla.
###
