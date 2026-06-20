# Contributing

We're building one system together; each person owns one service. Read
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) first — it's what keeps the three
services compatible.

## Who owns what

| Area | Owner | What to do |
|------|-------|------------|
| `services/service-a/` | __________ | Implement `/greet-service-b` + `/greeting-rcvd` |
| `services/service-b/` | __________ | Implement `/greet` |
| `services/service-c/` | __________ | Implement `/greet-c` |
| Shared infra (`services/lib/`, `nginx/`, `systemd/`, `scripts/`, docs) | __________ | Owner / coordinate changes |

> **Only edit your own `services/service-X/` folder.** If you think `lib/` or the
> contract needs a change, raise it with the team first — those files affect
> everyone and cause merge conflicts.

## One-time setup

```bash
git clone git@github.com:mercykilonzo/Devops.git
cd Devops
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/service-a/requirements.txt   # django + gunicorn
```

## Run everything locally (no VM needed)

```bash
./scripts/run-local.sh
# in another terminal:
curl -s http://127.0.0.1:3001/health
curl -s http://127.0.0.1:3002/health
curl -s http://127.0.0.1:3003/health
```

`/health` works out of the box for all three. As each person implements their
endpoint, the full flow starts working:
```bash
curl -s -H "X-Request-ID: t1" http://127.0.0.1:3001/greet-service-b
```

## Git workflow (nobody commits to `main` directly)

```bash
git checkout main && git pull origin main
git checkout -b <name>/service-c        # e.g. mercy/service-c
# ... edit only services/service-c/ ...
git add services/service-c/
git commit -m "Service C: implement /greet-c + callback"
git push -u origin <name>/service-c
# then open a Pull Request into main on GitHub; a teammate reviews + merges
```

Keep commits small, pull `main` often, and your service folder won't conflict
with anyone else's.

## Definition of done for a service

- [ ] `/health` returns 200 (already done)
- [ ] Your work endpoint(s) implemented per the contract
- [ ] Every log line includes `request_id`; `X-Request-ID` is forwarded on
      outbound calls
- [ ] `./scripts/run-local.sh` runs and your endpoint returns the contracted JSON
- [ ] PR opened and reviewed by at least one teammate
