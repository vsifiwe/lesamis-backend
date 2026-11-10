# Deploy the Les Amis API

Pushes to `main`, `staging`, and `dev` deploy the Django backend automatically. Next.js continues to deploy from its own repository through Netlify.

| Branch | GitHub Environment | VPS user | API hostname | VPS upstream |
| --- | --- | --- | --- | --- |
| `main` | `production` | `lesamis-production` | `api.lesamis.rw` | `127.0.0.1:8101` |
| `staging` | `staging` | `lesamis-staging` | `api-staging.lesamis.rw` | `127.0.0.1:8102` |
| `dev` | `dev` | `lesamis-dev` | `api-dev.lesamis.rw` | `127.0.0.1:8103` |

## 1. Prepare the VPS and DNS

On Ubuntu 24.04, install [Docker Engine 28 or newer and the Compose plugin](https://docs.docker.com/engine/install/ubuntu/) and [Caddy as a host service](https://caddyserver.com/docs/install#debian-ubuntu-raspbian). Install `git` and `curl`. Allow TCP 80 and 443 for Caddy and the configured SSH port for GitHub-hosted runners. The three Gunicorn ports listen on loopback. PostgreSQL has no published port.

In Cloudflare, create DNS-only (gray cloud) A records for `api`, `api-staging`, and `api-dev` pointing to the VPS IPv4 address. Check for existing records before changing them. Caddy obtains the certificates once DNS resolves and the VPS is reachable.

Copy the backend checkout to the server without any local `.env` files. From that checkout, run these one-time setup commands as the VPS administrator.

```bash
sudo install -d -m 0755 /usr/local/lib/les-amis /etc/les-amis /opt/les-amis /srv/les-amis-static
sudo install -m 0755 deployment/deploy.sh /usr/local/lib/les-amis/deploy.sh
sudo install -m 0644 deployment/compose.yml /usr/local/lib/les-amis/compose.yml

for env in production staging dev; do
  account="lesamis-$env"
  sudo useradd --system --user-group --create-home --shell /bin/bash "$account"
  sudo usermod -aG docker "$account"
  sudo passwd "$account"
  sudo install -d -m 0700 -o "$account" -g "$account" \
    "/opt/les-amis/$env" "/opt/les-amis/$env/backups"
  sudo install -d -m 0755 -o "$account" -g "$account" \
    "/srv/les-amis-static/$env" "/srv/les-amis-static/$env/releases"
  sudo install -m 0640 -o root -g "$account" deployment/app.env.example \
    "/etc/les-amis/$env.env"
done
```

Edit the three files under `/etc/les-amis`. Generate a distinct `SECRET_KEY` and `DB_PASSWORD` for each with `openssl rand -hex 32`. Set `ALLOWED_HOSTS` to the matching hostname in the table and `CSRF_TRUSTED_ORIGINS` to the matching HTTPS origin. For production set `CORS_ALLOWED_ORIGINS=https://lesamis.rw,https://www.lesamis.rw`. In staging and dev, allow only the actual frontend origins used for testing. Keep `DB_HOST=postgres` and keep each database's credentials stable after initial deployment.

```bash
sudo install -m 0644 deployment/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now docker caddy
sudo systemctl reload caddy
```

The server uses its installed deployment script and Compose configuration. Review and reinstall those files as an administrator when changing the deployment infrastructure. Access to the Docker group is equivalent to administrative access, so restrict pushes to all three deployment branches to trusted maintainers.

## 2. Configure password SSH and GitHub

Set a strong, unique password for each deployment account at the `passwd` prompt. The SSH configuration enables password authentication for those accounts and forces each one to run the release command for its own environment. Install and validate it from an administrator session.

```bash
sudo install -m 0644 deployment/sshd.conf /etc/ssh/sshd_config.d/60-les-amis-deploy.conf
sudo sshd -t
sudo systemctl reload ssh
```

Keep the administrator session open while checking access. If you already provisioned the key-based setup, create the three new accounts and set their passwords. While deployments are idle, transfer ownership of each existing `/opt/les-amis/<environment>` and `/srv/les-amis-static/<environment>` tree to its new account and change the group of `/etc/les-amis/<environment>.env` to that account's group. Preserve the existing environment file contents. Replace the old SSH drop-in with the file above.

In `lesamis-backend`, open **Settings → Environments**. Create the three environments in the table. Set each deployment branch policy to **Selected branches and tags** and add exactly the mapped branch as a branch rule. Leave required reviewers and wait timers unset.

| Type | Name | Value |
| --- | --- | --- |
| Environment secret | `VPS_PASSWORD` | The matching deployment account password |
| Environment variable | `VPS_HOST` | VPS IP or DNS-only SSH hostname |
| Environment variable | `VPS_PORT` | SSH port, usually `22` |
| Environment variable | `VPS_USER` | The matching VPS user from the branch table |
| Environment variable | `VPS_KNOWN_HOSTS` | A known_hosts line using the server's verified Ed25519 public host key |

Read the public key from `/etc/ssh/ssh_host_ed25519_key.pub` through the trusted VPS console. Prefix the key type and key data with `VPS_HOST` for port 22 or `[VPS_HOST]:VPS_PORT` for any other port. Paste that line into `VPS_KNOWN_HOSTS`.

If switching an existing setup, remove the old `VPS_DEPLOY_KEY` secrets and retire the old `lesamis-deploy` account after confirming the new deployments work.

## 3. Roll out and verify

Check the remote branches with `git ls-remote --heads origin main staging dev`. Put the reviewed workflow and application commit on `dev` first, creating the branch if absent. Then promote the commit to `staging` and finally `main`. Use the existing branch history when a branch already exists.

- Check `/healthz/`, `/api/v1/docs/`, and `/static/admin/css/base.css` over each public HTTPS hostname. Confirm that unauthenticated requests to `/api/v1/members/` and `/api/v1/fund-accounts/balances/` are rejected. Point the production Netlify build at `NEXT_PUBLIC_API_URL=https://api.lesamis.rw` and confirm login and an API-backed page.
- On dev, confirm a second push updates only dev and preserves data. To exercise the remote migration failure path, temporarily set `DB_HOST=invalid.invalid` in the dev environment file and rerun the current commit. Restore `DB_HOST=postgres` and rerun to recover. Verify that an older workflow rerun reports **Release superseded** and that other branch pushes and tags do not deploy.
- Check that each new database contains its own workbook import. The same historical records are seeded in all three databases. The APIs are publicly reachable and Django protects authenticated endpoints. The committed workbook fixture itself is readable in the public backend repository.

## 4. Recover a failed release

The Actions job reports the failing stage. Read `/opt/les-amis/<environment>/deploy.log` on the VPS for details. The file `/opt/les-amis/<environment>/successful` lists the most recent successful SHA on line one and the previous one, if present, on line two. If a failure happens after services are stopped, the recorded release stays the same and the web and scheduler may be down. Fix the problem and rerun the branch head, or restart a retained image and static files from the VPS console.

```bash
sudo -u lesamis-dev /usr/local/lib/les-amis/deploy.sh rollback dev RETAINED_SHA
```

Before running this command, check that the selected code supports the current database schema. If it does not, identify and verify the matching pre-deployment dump in `/opt/les-amis/<environment>/backups`. To explicitly replace the database from that dump, pass its basename as the final argument.

```bash
sudo -u lesamis-dev /usr/local/lib/les-amis/deploy.sh rollback dev RETAINED_SHA BACKUP_BASENAME
```

The restore takes a fresh backup first, then replaces the selected environment's database. Writes after the selected dump are absent from the restored database. The release keeps two successful images and their static files, plus the seven newest pre-deploy dumps per environment. Keep any required longer-term copies outside the managed backup directory.
