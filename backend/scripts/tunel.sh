#!/usr/bin/env bash
# La API corriendo en este computador y expuesta a internet con un túnel de Cloudflare, para que el
# front de Render la use. Uso: `make tunel` (ver DEV.md, "API local con túnel").
#
# Dos modos:
#   - Túnel rápido (por defecto): no pide cuenta. Cloudflare da una URL *.trycloudflare.com que cambia
#     cada vez que se reinicia el túnel, así que hay que apuntar el front a la URL nueva. Si están
#     RENDER_API_KEY y RENDER_FRONT_ID, el script lo hace solo: cambia VITE_API_URL en Render y redespliega el front.
#   - Túnel con nombre: TUNEL_NOMBRE=bifurca TUNEL_URL=https://api.tudominio.cl make tunel
#     URL fija (pide un dominio en Cloudflare y `cloudflared tunnel login` una vez). El front no se toca más.
#
# Variables (todas opcionales; también se leen de backend/.env.tunel si existe):
#   PORT              puerto local de la API (8000)
#   WEB_CONCURRENCY   procesos de uvicorn (4: aquí hay más CPU y RAM que en Render free)
#   FRONT_URL         origen del front, para CORS (https://bifurca.onrender.com)
#   TUNEL_NOMBRE, TUNEL_URL          túnel con nombre y su URL pública
#   RENDER_API_KEY, RENDER_FRONT_ID  para actualizar el front solo (Render > Account Settings > API Keys;
#                                    el id srv-... sale en la URL del servicio en el dashboard)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env.tunel ]; then
    set -a; . ./.env.tunel; set +a
fi

PORT="${PORT:-8000}"
FRONT_URL="${FRONT_URL:-https://bifurca.onrender.com}"
export PORT
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
# Una variable de entorno pesa más que backend/.env: así el front de Render puede llamar a la API.
export CORS_ORIGINS="${CORS_ORIGINS:-[\"$FRONT_URL\",\"http://localhost:5173\"]}"

if ! command -v cloudflared >/dev/null 2>&1; then
    echo "Falta cloudflared: brew install cloudflared" >&2
    exit 1
fi
if curl -fsS -m 2 -o /dev/null "http://localhost:$PORT/health" 2>/dev/null; then
    echo "Ya hay algo escuchando en el puerto $PORT. Ciérralo o usa PORT=8001 make tunel" >&2
    exit 1
fi

LOG_TUNEL="$(mktemp "${TMPDIR:-/tmp}/bifurca-tunel.XXXXXX")"
PIDS=()
terminar() {
    trap - EXIT INT TERM
    for pid in ${PIDS[@]+"${PIDS[@]}"}; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null || true
    rm -f "$LOG_TUNEL"
}
trap terminar EXIT INT TERM

# Que el Mac no se duerma mientras corre (solo macOS)
if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -dims -w $$ &
    PIDS+=($!)
fi

echo "Levantando la API en http://localhost:$PORT con $WEB_CONCURRENCY procesos (CORS: $CORS_ORIGINS)"
scripts/prod.sh &
PIDS+=($!)
API_PID=$!

for _ in $(seq 1 60); do
    curl -fsS -m 2 -o /dev/null "http://localhost:$PORT/health" 2>/dev/null && break
    kill -0 "$API_PID" 2>/dev/null || { echo "La API no arrancó" >&2; exit 1; }
    sleep 1
done

if [ -n "${TUNEL_NOMBRE:-}" ]; then
    : "${TUNEL_URL:?Con TUNEL_NOMBRE falta TUNEL_URL, la URL pública del túnel (https://api.tudominio.cl)}"
    cloudflared tunnel --no-autoupdate run --url "http://localhost:$PORT" "$TUNEL_NOMBRE" >"$LOG_TUNEL" 2>&1 &
    PIDS+=($!)
    URL="${TUNEL_URL%/}"
else
    cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LOG_TUNEL" 2>&1 &
    PIDS+=($!)
    URL=""
    for _ in $(seq 1 30); do
        URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_TUNEL" | head -1 || true)"
        [ -n "$URL" ] && break
        sleep 1
    done
    if [ -z "$URL" ]; then
        echo "cloudflared no entregó una URL. Su log:" >&2
        cat "$LOG_TUNEL" >&2
        exit 1
    fi
fi
TUNEL_PID=$!

echo "Esperando que $URL/health responda (el DNS del túnel tarda unos segundos)..."
for _ in $(seq 1 60); do
    curl -fsS -m 5 -o /dev/null "$URL/health" 2>/dev/null && break
    sleep 2
done
if ! curl -fsS -m 5 -o /dev/null "$URL/health" 2>/dev/null; then
    echo "Aviso: $URL/health todavía no responde desde aquí. Puede ser el DNS local; prueba en el navegador." >&2
fi

if [ -n "${RENDER_API_KEY:-}" ] && [ -n "${RENDER_FRONT_ID:-}" ]; then
    actual="$(curl -fsS -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$RENDER_FRONT_ID/env-vars/VITE_API_URL" 2>/dev/null \
        | python3 -c 'import sys, json; print(json.load(sys.stdin).get("value", ""))' 2>/dev/null || true)"
    if [ "$actual" = "$URL" ]; then
        echo "El front de Render ya apunta a $URL"
    else
        echo "Apuntando el front de Render a $URL y redesplegándolo (1 a 2 minutos)"
        curl -fsS -X PUT -o /dev/null -H "Authorization: Bearer $RENDER_API_KEY" -H "Content-Type: application/json" \
            -d "{\"value\": \"$URL\"}" "https://api.render.com/v1/services/$RENDER_FRONT_ID/env-vars/VITE_API_URL"
        curl -fsS -X POST -o /dev/null -H "Authorization: Bearer $RENDER_API_KEY" -H "Content-Type: application/json" \
            -d '{"clearCache": "do_not_clear"}' "https://api.render.com/v1/services/$RENDER_FRONT_ID/deploys"
    fi
elif [ -z "${TUNEL_NOMBRE:-}" ]; then
    echo
    echo "Pon VITE_API_URL=$URL en el front de Render (Environment) y redespliégalo."
    echo "O define RENDER_API_KEY y RENDER_FRONT_ID en backend/.env.tunel para que el script lo haga solo."
fi

echo
echo "API pública: $URL   (docs: $URL/docs)"
echo "Ctrl+C para cerrar la API y el túnel."

# Si se cae la API o el túnel, se cierra todo (bash 3.2 de macOS no tiene `wait -n`)
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$TUNEL_PID" 2>/dev/null; do
    sleep 5
done
echo "Se cayó la API o el túnel. Log del túnel:" >&2
tail -20 "$LOG_TUNEL" >&2
exit 1
