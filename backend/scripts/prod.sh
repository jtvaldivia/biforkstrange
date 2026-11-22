#!/usr/bin/env sh
# Arranque de producción (Render): varios procesos de uvicorn, sin --reload.
#
# Una partida corre el motor en CPU (numpy) dentro del request: con un solo proceso, diez /partida a la
# vez se atienden en fila (2,5 s la última, en un Mac; 1,1 s con 4 procesos). Cada proceso tiene su
# propia copia del paquete: ~80 MB al partir y ~170 MB después de jugar.
#
#   PORT             lo define Render (8000 en local)
#   WEB_CONCURRENCY  cuántos procesos: 2 por defecto, cabe en 512 MB. Más procesos solo ayudan si hay
#                    CPUs para ellos; súbelo a la cantidad de CPUs del plan si la RAM alcanza.
set -eu
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
    set -- uv run uvicorn
else
    set -- python -m uvicorn  # el entorno ya tiene las dependencias instaladas
fi
exec "$@" app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers --forwarded-allow-ips '*'
