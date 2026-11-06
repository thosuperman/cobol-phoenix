# Deployment

> Status: the Kiroween demo runs on an AWS Lightsail instance (see *Lightsail* below). The same Compose files run
> locally with `docker compose up --build`.

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

## AWS Lightsail (used for the hosted demo)

```
Route 53  cobol-phoenix.<domain>  A ─► Lightsail static IP
Lightsail small_3_0 in ap-southeast-1 (2 vCPU, 2 GB RAM, 60 GB SSD, Ubuntu 24.04), firewall 22/80/443 only
  └─ docker compose: caddy (HTTPS, Let's Encrypt) ─► frontend:3000 (localhost only) ─► backend:8000 (localhost only)
                     runner (network none, read-only, no capabilities)
```

1. Create the instance (Ubuntu 24.04, `small_3_0`), allocate and attach a static IP, open ports 22, 80, 443 only.
2. Create an A record for the hostname pointing at the static IP.
3. On the instance as root (if you pass this as Lightsail launch script, keep it POSIX `sh` — Lightsail does not honour a bash shebang):
   ```bash
   fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
   echo '/swapfile none swap sw 0 0' >> /etc/fstab
   apt-get update -y && apt-get install -y docker.io docker-compose-v2 docker-buildx git
   git clone https://github.com/thosuperman/cobol-phoenix.git /opt/cobol-phoenix
   ```
4. `cp deploy/lightsail.env.example .env`, set `PHOENIX_DOMAIN` / `PHOENIX_CORS_ORIGINS`, then:
   ```bash
   docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build
   ```
5. Verify `https://<host>/api/health` reports the executor `queue` as available.

Update: `git pull && docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build`.
Cost: the instance bundle price (USD 12/month at the time of writing) plus nothing else for this setup.

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
