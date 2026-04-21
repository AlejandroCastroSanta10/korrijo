#!/usr/bin/env bash
# Elimina recursivamente todos los __pycache__/ y .pyc del proyecto.
# Uso: ./scripts/clean-pycache.sh

set -euo pipefail

# Ejecuta desde la raíz del repo sin importar desde dónde se llame
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🧹 Limpiando caché de Python en $REPO_ROOT..."

# Contar antes de borrar (solo para el mensaje final)
pycache_count=$(find . -type d -name "__pycache__" -not -path "*/.venv/*" | wc -l)
pyc_count=$(find . -type f -name "*.pyc" -not -path "*/.venv/*" | wc -l)

# Borrar carpetas __pycache__
find . -type d -name "__pycache__" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true

# Borrar ficheros .pyc sueltos (por si acaso)
find . -type f -name "*.pyc" -not -path "*/.venv/*" -delete 2>/dev/null || true

echo "✅ Eliminadas $pycache_count carpetas __pycache__ y $pyc_count ficheros .pyc"