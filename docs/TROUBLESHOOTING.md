# Troubleshooting Guide

General method, every time:

1. **Logs** — `journalctl -u <svc> -n 50` (and `/var/log/nginx/platform_error.log`)
2. **Status** — `systemctl status <svc>`
3. **Connectivity** — `curl -v`, `ss -ltnp`, `getent hosts`
4. **Config** — the unit file, `/etc/hosts`, `nginx -T`

The `request_id` is your friend: grab it from the failing response/log and grep
every service for it.

---

## 1. Service startup failures

**Symptoms:** `systemctl status service-x` shows `failed` or `activating`.

```bash
systemctl status service-x
journalctl -u service-x -n 50 --no-pager
```

Common causes:
- **Port already in use** → `sudo ss -ltnp | grep :3002`; kill the stray process.
- **gunicorn/django not installed** → `python3 -m gunicorn --version` and
  `python3 -m django --version`; if missing, `sudo pip install django gunicorn`.
- **`ModuleNotFoundError: lib`** → `wsgi.py` adds `services/` to `sys.path`;
  ensure the app was deployed intact under `/opt/platform/services/`.
- **WSGI/import/syntax error** → the gunicorn traceback is in the journal.
- **Wrong path / permissions** → check `WorkingDirectory` and that
  `/opt/platform` is owned by `platform`.
- **Bad env** → `systemctl cat service-x` to see the `Environment=` lines
  (`DJANGO_SETTINGS_MODULE`, `PORT`, `SERVICE_*_URL`).

Fix the cause, then `sudo systemctl restart service-x`.

---

## 2. Service dependency failures (Service A won't start)

**Symptoms:** A stays in `activating (start-pre)` or repeatedly restarts.

A runs `wait-for-deps.sh` before starting and requires B and C.

```bash
systemctl status service-b service-c        # are deps up?
journalctl -u service-a -n 30                # look for "wait-for-deps: dependency NOT ready"
curl http://service-b.internal:3002/health  # can A reach B?
curl http://service-c.internal:3003/health
```

- If B or C is down → start them: `sudo systemctl start service-c service-b`.
- If deps are up but A still can't reach them → this is really a *discovery* or
  *network* problem (sections 4–6).
- Raise the gate timeout if startup is genuinely slow: edit
  `DEP_WAIT_TIMEOUT` in `service-a.service`, then `daemon-reload`.

> Reminder: stopping B or C **intentionally** also stops A (`Requires=`). That is
> expected behavior, not a bug.

---

## 3. Reverse proxy failures (502 / 504 / wrong response)

```bash
sudo nginx -t                                   # config valid?
systemctl status nginx
sudo tail -n 50 /var/log/nginx/platform_error.log
curl -v http://127.0.0.1:3001/health            # is Service A actually up?
```

- **502 Bad Gateway** → Service A is down or not on `127.0.0.1:3001`.
  `systemctl status service-a`, then restart it.
- **404 for `/service-a/...`** → route/typo in `platform.conf`; check the
  `location /service-a/` and `proxy_pass http://service_a_backend/` (both need
  trailing slashes).
- **Config changes not taking effect** → `sudo nginx -t && sudo systemctl reload nginx`.

---

## 4. Service discovery failures

**Symptoms:** logs show `request_failed` with `Name or service not known` or
`getaddrinfo` errors.

```bash
getent hosts service-b.internal             # expect: 127.0.0.1 service-b.internal
grep platform-service-discovery /etc/hosts
```

- Missing entries → `sudo ./scripts/setup-hosts.sh`.
- Resolves to the wrong address → fix the `/etc/hosts` line.
- App pointing at the wrong name → check `SERVICE_B_URL`/`SERVICE_C_URL` with
  `systemctl cat service-a`.

---

## 5. Name resolution failures

```bash
cat /etc/hosts
getent hosts service-c.internal
```

- If `/etc/hosts` was wiped/edited, re-run `sudo ./scripts/setup-hosts.sh`.
- `getent` uses NSS, the same path the app uses — if `getent` works but the app
  doesn't, restart the service (it may have cached a prior failure) and re-check.

---

## 6. Network access failures

Two opposite problems:

**(a) Internal call fails (should work):**
```bash
curl -v http://service-c.internal:3003/health   # from the VM
sudo ss -ltnp | grep -E ':3001|:3002|:3003'     # is it listening?
```
If not listening → the service is down (section 1). If listening on the wrong
address → check `BIND_ADDR`.

**(b) External access works but shouldn't (security hole):**
```bash
sudo ss -ltnp | grep :3002        # MUST show 127.0.0.1:3002, not 0.0.0.0:3002
sudo ufw status verbose           # MUST NOT allow 3001/3002/3003
```
If a service is bound to `0.0.0.0`, fix `BIND_ADDR=127.0.0.1` and restart. If
UFW allows a service port, remove the rule.

---

## 7. Missing logs

```bash
journalctl -u service-a --no-pager | tail
systemctl cat service-a | grep -E 'StandardOutput|PYTHONUNBUFFERED'
```

- No log lines at all → ensure `StandardOutput=journal` and
  `Environment=PYTHONUNBUFFERED=1` are present (Python block-buffers stdout
  otherwise). The logger also flushes per line, so this is belt-and-braces.
- Looking in the wrong place → app logs are in **journald** (not a file);
  Nginx logs are in `/var/log/nginx/platform_access.json` and `platform_error.log`.

---

## 8. Invalid routing behavior

```bash
sudo nginx -T | sed -n '/server {/,/^}/p'       # see the live server block
curl -i http://localhost/service-a/health        # expect 200
curl -i http://localhost/service-b/health        # expect 404 (no route)
curl -i http://localhost/anything                # expect 404 JSON
```

If `/service-a/health` returns the wrong upstream path, re-check the trailing
slashes on `location` and `proxy_pass`.

---

## 9. Inter-service communication failures

Trace the exact hop that breaks using one request id:

```bash
RID="diag-$(date +%s)"
curl -s -H "X-Request-ID: $RID" http://localhost/service-a/greet-service-b
journalctl -t service-a -t service-b -t service-c -o cat | grep "$RID"
```

Read the chain of events:
- Stops after A `calling_downstream` (no B `request_received`) → A→B is broken
  (B down, discovery, or firewall).
- Stops after B `request_forwarded` attempt → B→C is broken.
- C `callback_sent` but no A `callback_received` → C→A callback is broken
  (check `SERVICE_A_URL` and that A is up).
- A `request_failed` with `502` → expected graceful degradation; fix the named
  downstream and retry.

---

## Quick command cheat-sheet

```bash
# status & logs
systemctl status service-a service-b service-c
journalctl -u service-a -f
journalctl -t service-a -t service-b -t service-c -o cat | grep <request_id>

# connectivity & discovery
getent hosts service-b.internal
curl -v http://service-c.internal:3003/health
sudo ss -ltnp | grep -E ':3001|:3002|:3003'

# proxy & firewall
sudo nginx -t && sudo nginx -T
sudo ufw status verbose

# recover
sudo systemctl restart service-c service-b service-a
sudo ./scripts/healthcheck.sh
```
