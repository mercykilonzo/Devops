# Submission — CI/CD for Containerized Microservices

**Repository:** https://github.com/mercykilonzo/Devops
**Group:** _<your group name>_
**Deployed commit:** `b24d844137d7cec4f5a53b936c4fab8ab3aebbfa`
**Image tag:** `sha-b24d844`

---

## 1–6. Deliverables

| # | Deliverable | Link / value |
|---|-------------|--------------|
| 1 | GitHub repository | https://github.com/mercykilonzo/Devops |
| 2 | Pull request showing CI validation | https://github.com/mercykilonzo/Devops/pull/5 — `verify` (×3) + `verify-compose` green; `publish` correctly **skipped** on the PR |
| 3 | Successful GitHub Actions run on `main` | https://github.com/mercykilonzo/Devops/actions/runs/28674891759 — `verify` + `verify-compose` + `publish` all green |
| 4 | Docker Hub images (public) | `mwikalik/devops-service-a:sha-b24d844`<br>`mwikalik/devops-service-b:sha-b24d844`<br>`mwikalik/devops-service-c:sha-b24d844` |
| 5 | Commit hash used for deployment | `b24d844137d7cec4f5a53b936c4fab8ab3aebbfa` (tag `sha-b24d844`) |
| 6 | README deployment section | https://github.com/mercykilonzo/Devops#container-cicd-deployment |

Docker Hub repos: https://hub.docker.com/r/mwikalik/devops-service-a · `-b` · `-c`

---

## How to review / run it (from the published images — no build)

**Prerequisites:** Docker + Docker Compose.

```bash
git clone https://github.com/mercykilonzo/Devops.git
cd Devops

export DOCKERHUB_USERNAME=mwikalik
export APP_NAME=devops
./scripts/deploy.sh sha-b24d844
```

This pulls the commit-pinned images and starts the stack (it does **not** build
locally). Then verify:

```bash
docker compose -f docker-compose.prod.yml ps          # all services up; only nginx on :8080
curl http://localhost:8080/service-a/health           # 200
curl -H "X-Request-ID: review-1" \
     http://localhost:8080/service-a/greet-service-b   # full A→B→C→A flow: "success"
```

Prove the images are pullable and commit-pinned:

```bash
docker pull mwikalik/devops-service-a:sha-b24d844
docker image inspect mwikalik/devops-service-a:sha-b24d844 \
  --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
```

Tear down:

```bash
docker compose -f docker-compose.prod.yml down
```

---

## What the pipeline guarantees (for the reviewer's checklist)

- **CI runs tests before the Docker build** — `verify` job: install deps →
  `python manage.py test` → `manage.py check` → `docker build`.
- **PRs verify only; images publish only on `main`** — `publish` is gated to
  `push` on `main` and was skipped on PR #5.
- **Images are commit-SHA tagged** (`sha-b24d844`), never `latest`, with
  `image.revision` + `image.source` labels.
- **Production Compose pulls images** (`image:`, not `build:`); `IMAGE_TAG`
  controls the version.
- **Only Nginx publishes a host port** (`8080`); Service B and C are internal
  (`backend` network is `internal: true`).
- **Hardening:** non-root containers, per-service health checks, named
  `frontend`/`backend` networks, graceful shutdown, `server_tokens off`.
- **No secrets committed** — `DOCKERHUB_TOKEN` is a GitHub Secret,
  `DOCKERHUB_USERNAME` a GitHub Variable; only `.env.example` is in the repo.

Validation evidence: [`docs/CONTAINER_VALIDATION.md`](docs/CONTAINER_VALIDATION.md)

---


