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

# Only ever deploy commit-pinned images — reject "latest" or malformed tags.
if [[ ! "$IMAGE_TAG" =~ ^sha-[0-9a-f]{7,40}$ ]]; then
  echo "Invalid IMAGE_TAG '$IMAGE_TAG' — expected sha-<7-40 hex> (e.g. sha-a1b2c3d)."
  exit 1
fi

# The gateway (nginx) config is bind-mounted from this checkout, so it is NOT
# pinned to the image tag the way the app images are. Assert the checkout
# matches the tag being deployed so gateway behaviour can't silently drift.
if git rev-parse --git-dir >/dev/null 2>&1; then
  checkout_sha="sha-$(git rev-parse --short=7 HEAD)"
  if [ "$checkout_sha" != "${IMAGE_TAG:0:11}" ]; then
    echo "WARNING: checkout is $checkout_sha but deploying $IMAGE_TAG."
    echo "         The bind-mounted nginx config may not match the deployed images."
    echo "         Run 'git checkout ${IMAGE_TAG#sha-}' first, or press Ctrl-C to abort."
    sleep 5
  fi
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
# --wait: exit only once every service passes its health check (or fail).
docker compose -f docker-compose.prod.yml up -d --remove-orphans --wait
docker compose -f docker-compose.prod.yml ps
