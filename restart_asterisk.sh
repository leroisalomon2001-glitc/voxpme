#!/bin/bash
set -e
CONTAINER="voxpme-asterisk"
MAX_WAIT=30

echo "→ Restart du conteneur $CONTAINER..."
docker restart "$CONTAINER"

echo "→ Attente que Asterisk réponde..."
elapsed=0
while ! docker exec "$CONTAINER" asterisk -rx "core show version" &>/dev/null; do
    sleep 1
    elapsed=$((elapsed+1))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "✗ Asterisk n'a pas redémarré après ${MAX_WAIT}s"
        exit 1
    fi
done

echo "✓ Asterisk répond après ${elapsed}s"
docker exec "$CONTAINER" asterisk -rx "http show status"
