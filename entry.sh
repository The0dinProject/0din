#!/bin/sh
gunicorn -w 4 -b 0.0.0.0:${NODE_PORT:-5000} 0din:app --log-level debug --access-logfile - --error-logfile -
