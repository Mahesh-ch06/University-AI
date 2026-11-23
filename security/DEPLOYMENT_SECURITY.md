# Deployment security

What must be set on the hosting dashboards. None of it could be checked or changed from the repository: every
item is **BLOCKED** until someone with dashboard access does it and records the date.

## 1. Render (backend)

| Setting | Required value | Why |
|---|---|---|
| `APP_ENV` | `production` | Locks the placeholder admin key, hides `/docs`, enables HSTS (also detected through Render's `RENDER` variable) |
| `APP_DEBUG` | `false` | Same, and the start-up warning goes away |
| `ADMIN_API_KEY` | 32+ random characters (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) | The only admin credential. **Rotate it now** if it was ever placed in a URL ("Open live chat" / "Copy chat link" in older versions put it in links, history and logs) |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | The production site(s) only. Remove any `.*\.vercel\.app` value | An explicit Render value overrides the safer code default |
| `TRUSTED_PROXY_HOPS` | `1` (verify; see below) | Correct client IP for rate limits |
| `CLIENT_IP_HEADER` | Set only if Render documents a trusted client-IP header | |
| `REDIS_URL` | A Redis with a password, TLS (`rediss://`), not publicly reachable | Rate-limit counters shared across instances |
| `DATABASE_URL` | Neon URL with `sslmode=require`; a role with only the privileges the app needs (no superuser) | Least privilege |
| `GEMINI_API_KEYS` | Keys restricted to the Generative Language API, with a quota / budget alert | Denial of wallet |
| AI limits | Defaults are fine to start; tune `AI_IP_DAILY_LIMIT` if colleges share one IP | |

**Verify the client IP setting once deployed (no secrets involved):**

```bash
curl -s -H "X-Forwarded-For: 1.2.3.4" -H "X-Admin-Key: wrong" https://<backend>/api/v1/admin/stats -o /dev/null -w "%{http_code}\n"
```

Repeat it 6 times with different fake addresses. The 6th call must return `429`. If it keeps returning `403`,
Render adds more than one hop: raise `TRUSTED_PROXY_HOPS`.

## 2. Vercel (frontend)

| Setting | Required value |
|---|---|
| `VITE_API_BASE_URL` | The exact Render URL (e.g. `https://university-ai-luwe.onrender.com`). Then narrow `connect-src` in `vercel.json` from `https://*.onrender.com` to that host |
| `VITE_ADMIN_PATH` | A private random slug (hides the admin page; the key is the real control) |
| Deployment protection | Enable for preview deployments (previews share the production API) |
| Headers | `vercel.json` is the source of truth. Confirm in the browser: DevTools > Network > Response headers on `/` |

## 3. Database (Neon / PostgreSQL)

- Encryption at rest, backups and point-in-time recovery: confirm the plan, and record the region.
- Restrict network access (IP allow list / private networking) if the plan allows it.
- Separate the admin / migration role from the application role.

## 4. Container

- The image runs as root today. Recommended (test on a Render preview first, because a mounted disk must be
  writable by the new user):

  ```dockerfile
  RUN useradd --create-home --uid 10001 app && chown -R app /app
  USER app
  ```

- `build-essential` is installed in the final image; a multi-stage build would keep compilers out of production.
- Pin Python dependencies: generate a lock file (`pip-compile` / `uv pip compile`) from `requirements.txt` on
  Python 3.12 and install from it. Dependabot (`.github/dependabot.yml`) then proposes updates.

## 5. GitHub

- Branch protection on `main`: pull requests, review, required checks.
- Secret scanning and push protection: Settings > Code security.
- Dependabot alerts on (the config file only schedules version-update PRs).

## 6. Release checklist

1. Backend tests: `cd backend && python -m pytest -q` (the 9 known environment-dependent failures need
   PostgreSQL / Redis / an API key).
2. Frontend: `npm run build && npm test && npm audit`.
3. `pip-audit -r backend/requirements.txt`.
4. Browser checks: `security/tests/frontend_security_ui.cjs`.
5. After deploy: the client-IP check above; `/docs` returns 404; response headers present.
