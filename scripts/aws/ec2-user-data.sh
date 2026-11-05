#!/bin/bash
# EC2 user data for a single-host COBOL Phoenix deployment (Amazon Linux 2023).
# Edit REPO_URL (and optionally DOMAIN) before use. Not executed by the project authors.
set -euxo pipefail
REPO_URL="https://github.com/thosuperman/cobol-phoenix.git"
DOMAIN=""   # e.g. phoenix.example.com for automatic TLS via Caddy

dnf install -y docker git
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -sSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

git clone "$REPO_URL" /opt/cobol-phoenix
cd /opt/cobol-phoenix
cp .env.example .env
sed -i 's/^PHOENIX_COBOL_EXECUTOR=.*/PHOENIX_COBOL_EXECUTOR=queue/' .env
if [ -n "$DOMAIN" ]; then
  sed -i "s#^PHOENIX_CORS_ORIGINS=.*#PHOENIX_CORS_ORIGINS=https://$DOMAIN#" .env
fi
docker compose up --build -d

if [ -n "$DOMAIN" ]; then
  docker run -d --name caddy --restart unless-stopped --network host \
    -v caddy-data:/data caddy:2.8 caddy reverse-proxy --from "$DOMAIN" --to localhost:3000
fi
