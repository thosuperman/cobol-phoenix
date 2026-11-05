# Deployment

> Status: deployment configuration is complete and `docker compose up --build` was run locally (see
> CHANGELOG). **No public cloud deployment has been performed** — it requires the owner's cloud account.

## Single host with Docker Compose (recommended)

```bash
cp .env.example .env            # optional overrides
docker compose up --build -d
open http://localhost:3000
```

| Service | Purpose | Hardening |
|---|---|---|
| `frontend` | Next.js standalone server, proxies `/api` to the backend | non-root `node` user, health check |
| `backend` | FastAPI + Alembic migrations on start, SQLite on the `phoenix-data` volume | uid 10001, `no-new-privileges`, health check `/api/health` |
| `runner` | GnuCOBOL sandbox consuming `phoenix-jobs` | `network_mode: none`, `read_only`, tmpfs `/tmp`, `cap_drop: ALL`, `no-new-privileges`, 1 GB RAM, 1 CPU, 256 PIDs, per-process rlimits and timeouts |

Persistent data: volume `phoenix-data` (database, imported sources, generated projects). Back it up with
`docker run --rm -v kiroween_phoenix-data:/d -v $PWD:/b alpine tar czf /b/phoenix-data.tgz -C /d .`.

### PostgreSQL

Set `PHOENIX_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/phoenix` and add the driver
(`pip install "psycopg[binary]"`) to the backend image. Models are PostgreSQL compatible; run
`alembic upgrade head` (the container entrypoint does this automatically).

### Database migrations

```bash
cd backend
alembic upgrade head                               # apply
alembic revision --autogenerate -m "describe"      # after model changes
```

### TLS / reverse proxy

Expose only the frontend (`PHOENIX_WEB_PORT`) behind a TLS-terminating proxy (Caddy, nginx, ALB). The backend
port mapping can be removed in production; the frontend reaches it on the internal network.

## Optional AWS architecture (cost-conscious)

```
Route 53 ─► EC2 t3.medium (Amazon Linux 2023, 30 GB gp3)
             └─ docker compose: frontend · backend · runner (network none)
             └─ Caddy (TLS via Let's Encrypt) ─► frontend:3000
EBS snapshot (daily, Data Lifecycle Manager) for the phoenix-data volume
```

Why EC2 instead of ECS Fargate: the sandbox relies on `network_mode: none` and a shared job volume, which
Fargate's `awsvpc` networking does not provide; a single small instance also keeps cost around the price of one
t3.medium plus storage.

Steps (manual, require your AWS account):

1. Launch an Amazon Linux 2023 instance (t3.medium or larger), security group allowing 22 (your IP) and 80/443.
2. Paste [`scripts/aws/ec2-user-data.sh`](../scripts/aws/ec2-user-data.sh) as user data (installs Docker,
   clones the repository, starts compose). Set `REPO_URL` first.
3. Point a DNS record at the instance and set `DOMAIN` in the script to enable automatic TLS with Caddy.
4. Verify: `curl https://<domain>/api/health` returns `{"status":"ok", ...}` and the executor is available.
