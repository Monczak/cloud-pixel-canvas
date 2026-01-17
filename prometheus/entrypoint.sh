#!/bin/sh

if [ -n "$BACKEND_HOST" ]; then
    echo "Updating prometheus.yml target to $BACKEND_HOST..."
    sed -i "s/backend:8000/$BACKEND_HOST/g" /etc/prometheus/prometheus.yml
fi

exec /bin/prometheus "$@"
