#!/bin/sh

if [ "${ENABLE_SSL}" = "true" ]; then
    gunicorn -w 4 -b 0.0.0.0:${NODE_PORT:-5000} 0din:app \
        --certfile=cert.pem --keyfile=key.pem \
        --log-level debug --access-logfile - --error-logfile -
else
    gunicorn -w 4 -b 0.0.0.0:${NODE_PORT:-5000} 0din:app \
        --log-level debug --access-logfile - --error-logfile -
fi

