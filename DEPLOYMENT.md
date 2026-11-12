# Deploy the Les Amis API

Pushes to `main`, `staging`, and `dev` deploy the Django backend automatically. Next.js continues to deploy from its own repository through Netlify.

| Branch | VPS stack | API hostname | VPS upstream |
| --- | --- | --- | --- |
| `main` | `production` | `api.lesamis.rw` | `127.0.0.1:8101` |
| `staging` | `staging` | `api-staging.lesamis.rw` | `127.0.0.1:8102` |
| `dev` | `dev` | `api-dev.lesamis.rw` | `127.0.0.1:8103` |

## 1. Prepare the VPS and DNS

On Ubuntu 24.04, install [Docker Engine 28 or newer and the Compose plugin](https://docs.docker.com/engine/install/ubuntu/) and [Caddy as a host service](https://caddyserver.com/docs/install#debian-ubuntu-raspbian). Install `git` and `curl`. Allow TCP 80 and 443 for Caddy and the configured SSH port for GitHub-hosted runners. The three Gunicorn ports listen on loopback. PostgreSQL has no published port.

In Cloudflare, create DNS-only (gray cloud) A records for `api`, `api-staging`, and `api-dev` pointing to the VPS IPv4 address. Check for existing records before changing them. Caddy obtains the certificates once DNS resolves and the VPS is reachable.

Copy the backend checkout to the server without any local `.env` files. From that checkout, run these one-time setup commands as the VPS administrator.

```bash
sudo install -d -m 0755 /usr/local/lib/les-amis /etc/les-amis /opt/les-amis /srv/les-amis-static
sudo install -m 0755 deployment/deploy.sh /usr/local/lib/les-amis/deploy.sh
sudo install -m 0644 deployment/compose.yml /usr/local/lib/les-amis/compose.yml

sudo useradd --system --user-group --create-home --shell /bin/bash lesamis-deploy
sudo usermod -aG docker lesamis-deploy
sudo passwd lesamis-deploy

for env in production staging dev; do
  sudo install -d -m 0700 -o lesamis-deploy -g lesamis-deploy \
    "/opt/les-amis/$env" "/opt/les-amis/$env/backups"
  sudo install -d -m 0755 -o lesamis-deploy -g lesamis-deploy \
    "/srv/les-amis-static/$env" "/srv/les-amis-static/$env/releases"
  sudo install -m 0640 -o root -g lesamis-deploy deployment/app.env.example \
    "/etc/les-amis/$env.env"
done
```

Edit the three files under `/etc/les-amis`. Generate a distinct `SECRET_KEY` for each with `openssl rand -hex 32`. Set `ALLOWED_HOSTS` to the matching hostname in the table and `CSRF_TRUSTED_ORIGINS` to the matching HTTPS origin. For production set `CORS_ALLOWED_ORIGINS=https://lesamis.rw,https://www.lesamis.rw`. In staging and dev, allow only the actual frontend origins used for testing. For the bundled PostgreSQL container, keep `DB_HOST=postgres` and generate a distinct `DB_PASSWORD` for each database. Keep those credentials stable after initialization.

```bash
sudo install -m 0644 deployment/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now docker caddy
sudo systemctl reload caddy
```

The server uses its installed deployment script and Compose configuration. Review and reinstall those files as an administrator when changing the deployment infrastructure. Access to the Docker group is equivalent to administrative access, so restrict pushes to all three deployment branches to trusted maintainers.

### Use Supabase for an environment

Open the Supabase project's **Connect** panel. Use the direct connection if the VPS can reach it, or use **Session pooler** on port `5432` for an IPv4-only VPS. For example, put the session pooler values in `/etc/les-amis/staging.env`.

```dotenv
DB_HOST=<session pooler hostname from Connect>
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.<project-ref>
DB_PASSWORD='<raw database password>'
PGSSLMODE=require
```

The direct endpoint typically uses `postgres` as the username. Copy the host and username from the selected connection. Use a separate database for each deployment environment.

With an external `DB_HOST`, the script checks the connection before stopping application services. Use Supabase backups for that database. The deployment applies Django migrations to the configured database. Transfer any existing application data you need from the bundled database before switching. On an existing VPS, reinstall the updated `deployment/deploy.sh` using the install command above, then rerun the latest deployment for the branch.

## 2. Configure password SSH and GitHub

Set one strong password for `lesamis-deploy` at the `passwd` prompt. The SSH configuration restricts that account to the release command. The account can deploy all three stacks. Install and validate the configuration from an administrator session.

```bash
sudo install -m 0644 deployment/sshd.conf /etc/ssh/sshd_config.d/60-les-amis-deploy.conf
sudo sshd -t
sudo systemctl reload ssh
```

Keep the administrator session open while checking access. If migrating from separate deployment accounts, create the shared account and set its password. While deployments are idle, run the following commands, then install the new SSH drop-in and reload SSH as shown above.

```bash
sudo usermod -aG docker lesamis-deploy
for env in production staging dev; do
  sudo usermod --lock --expiredate 1970-01-02 "lesamis-$env"
  sudo chown -hR lesamis-deploy:lesamis-deploy "/opt/les-amis/$env" "/srv/les-amis-static/$env"
  sudo chgrp lesamis-deploy "/etc/les-amis/$env.env"
done
sudo install -m 0755 deployment/deploy.sh /usr/local/lib/les-amis/deploy.sh
```

In `lesamis-backend`, open **Settings → Environments** and create one environment named `vps`. Set its deployment branch policy to **Selected branches and tags** and add `main`, `staging`, and `dev` as branch rules. Leave required reviewers and wait timers unset.

| Type | Name | Value |
| --- | --- | --- |
| Environment secret | `VPS_PASSWORD` | The password for `lesamis-deploy` |
| Environment variable | `VPS_HOST` | VPS IP or DNS-only SSH hostname |
| Environment variable | `VPS_PORT` | SSH port, usually `22` |
The workflow pins the VPS public SSH host key under the alias `les-amis-vps`. If the VPS is rebuilt or its host key rotates, verify the new public key through the VPS console and update the pin in the workflow. After verifying the shared login, remove the old per-environment SSH variables and credentials from GitHub.

## 3. Roll out and verify

Check the remote branches with `git ls-remote --heads origin main staging dev`. Put the reviewed workflow and application commit on `dev` first, creating the branch if absent. Then promote the commit to `staging` and finally `main`. Use the existing branch history when a branch already exists.

- Check `/healthz/`, `/api/v1/docs/`, and `/static/admin/css/base.css` over each public HTTPS hostname. Confirm that unauthenticated requests to `/api/v1/members/` and `/api/v1/fund-accounts/balances/` are rejected. Point the production Netlify build at `NEXT_PUBLIC_API_URL=https://api.lesamis.rw` and confirm login and an API-backed page.
- On dev, confirm a second push updates only dev and preserves data. To exercise the database connection check, temporarily set `DB_HOST=invalid.invalid` in the dev environment file and rerun the current commit. Restore the original `DB_HOST` and rerun to recover. Verify that an older workflow rerun reports **Release superseded** and that other branch pushes and tags do not deploy.
- Check that each new database contains its own workbook import. The same historical records are seeded in all three databases. The APIs are publicly reachable and Django protects authenticated endpoints. The committed workbook fixture itself is readable in the public backend repository.

## 4. Recover a failed release

The Actions job reports the failing stage. Read `/opt/les-amis/<environment>/deploy.log` on the VPS for details. The file `/opt/les-amis/<environment>/successful` lists the most recent successful SHA on line one and the previous one, if present, on line two. If a failure happens after services are stopped, the recorded release stays the same and the web and scheduler may be down. Fix the problem and rerun the branch head, or restart a retained image and static files from the VPS console.

```bash
sudo -u lesamis-deploy /usr/local/lib/les-amis/deploy.sh rollback dev RETAINED_SHA
```

Before running this command, check that the selected code supports the current database schema. For an external database, use the database provider to restore a compatible backup if needed. For the bundled PostgreSQL database, identify and verify the matching pre-deployment dump in `/opt/les-amis/<environment>/backups` if you need to restore it. To explicitly replace the bundled database from that dump, pass its basename as the final argument.

```bash
sudo -u lesamis-deploy /usr/local/lib/les-amis/deploy.sh rollback dev RETAINED_SHA BACKUP_BASENAME
```

The restore takes a fresh backup first, then replaces the selected environment's database. Writes after the selected dump are absent from the restored database. The release keeps two successful images and their static files, plus the seven newest pre-deploy dumps per environment. Keep any required longer-term copies outside the managed backup directory.
