#!/bin/bash
set -e

URL="http://localhost:8000/health"

# We use -f to fail on HTTP errors
if curl -s -f "$URL" > /dev/null; then
    echo "✅ HEALTHY"
    exit 0
else
    echo "❌ UNHEALTHY"
    exit 1
fi
