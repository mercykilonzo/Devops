#!/usr/bin/env bash
#
# deploy.sh — deploy a specific, commit-pinned image version using the
# production Compose file. Never uses "latest".
#
#   export DOCKERHUB_USERNAME=<dockerhub-username>
#   export APP_NAME=<repo-name>          # optional; defaults to the folder name (lowercased)
#   ./scripts/deploy.sh sha-a1b2c3d
#
set -euo pipefail

IMAGE_TAG="${1:-}"

if [ -z "$IMAGE_TAG" ]; then
  echo "Usage:   ./scripts/deploy.sh sha-<short-commit-hash>"
  echo "Example: ./scripts/deploy.sh sha-a1b2c3d"
  exit 1
fi

export IMAGE_TAG
# Docker Hub repository names are lowercase.
export APP_NAME="${APP_NAME:-$(basename "$PWD" | tr '[:upper:]' '[:lower:]')}"

if [ -z "${DOCKERHUB_USERNAME:-}" ]; then
  echo "Missing DOCKERHUB_USERNAME (export it or set it in .env)"
  exit 1
fi

echo "Deploying ${APP_NAME} using image tag: ${IMAGE_TAG}"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml ps
