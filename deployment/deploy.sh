#!/usr/bin/env bash
set -euo pipefail
umask 077
export LC_ALL=C

die() {
    printf '%s\n' "$*" >&2
    exit 1
}

is_sha() {
    [[ "$1" =~ ^[0-9a-f]{40}$ ]]
}

mode=${1:-}
target=${2:-}
case "$target" in
    production) domain=api.lesamis.rw; WEB_PORT=8101 ;;
    staging) domain=api-staging.lesamis.rw; WEB_PORT=8102 ;;
    dev) domain=api-dev.lesamis.rw; WEB_PORT=8103 ;;
    *) die "Unknown deployment environment." ;;
esac

backup_name=
case "$mode" in
    receive)
        [[ $# == 2 ]] || die "Expected a forced SSH command."
        sha=${SSH_ORIGINAL_COMMAND:-}
        ;;
    rollback)
        [[ $# == 3 || $# == 4 ]] && [[ ! ${SSH_ORIGINAL_COMMAND+x} ]] ||
            die "Usage from the VPS console: deploy.sh rollback ENV SHA [BACKUP]"
        sha=$3
        backup_name=${4:-}
        ;;
    *) die "Expected receive or rollback." ;;
esac
is_sha "$sha" || die "Expected a full commit SHA."

root="/opt/les-amis/$target"
static_root="/srv/les-amis-static/$target"
image_repo="les-amis-$target"
export WEB_PORT
export APP_ENV_FILE="/etc/les-amis/$target.env"
export APP_IMAGE="$image_repo:$sha"
export STATIC_DIR="$static_root/releases/$sha"
export DEPLOY_UID="$(id -u)" DEPLOY_GID="$(id -g)"

[[ -r "$APP_ENV_FILE" && -d "$root/backups" && -d "$static_root/releases" ]] ||
    die "Provision the $target environment before deploying."
exec 9>"$root/deploy.lock"
flock -w 600 9 || die "Another $target deployment holds the lock."

compose() {
    docker compose --project-name "$image_repo" --env-file "$APP_ENV_FILE" \
        --file /usr/local/lib/les-amis/compose.yml "$@"
}

point_static_at() {
    local release=$1
    if [[ -n "$release" ]]; then
        ln -s "releases/$release" "$static_root/.current.$$"
        mv -Tf "$static_root/.current.$$" "$static_root/current"
    else
        rm -f -- "$static_root/current"
    fi
}

current=
previous=
if [[ -f "$root/successful" ]]; then
    { read -r current && read -r previous; } < "$root/successful" ||
        die "Invalid successful release record."
    is_sha "$current" && { [[ -z "$previous" ]] || is_sha "$previous"; } ||
        die "Invalid successful release record."
fi

if [[ "$mode" == rollback ]]; then
    [[ "$sha" == "$current" || "$sha" == "$previous" ]] || die "Choose a retained release."
    if [[ -n "$backup_name" ]]; then
        [[ "$backup_name" =~ ^[0-9]{8}T[0-9]{15}-before-[0-9a-f]{40}\.dump$ &&
           -s "$root/backups/$backup_name" ]] || die "Choose a backup from $target."
    fi
fi

# Public Actions logs get stage names. Command output stays on the server.
exec 3>&1 4>&2
exec >"$root/deploy.log" 2>&1
work=$(mktemp -d "$root/.deploy.XXXXXXXX")
cutover_started=false
backup_created=false
stage=prepare
shopt -s nullglob
finish() {
    local status=$?
    trap - EXIT
    set +e
    if (( status != 0 )); then
        if [[ "$cutover_started" == true ]]; then
            compose stop scheduler web </dev/null
            rm -f -- "$static_root/.current.$$"
            point_static_at "$current"
        fi
        printf 'Release %s failed during %s. See %s/deploy.log on the VPS.\n' \
            "$sha" "$stage" "$root" >&4
    fi
    if [[ "$backup_created" == true ]]; then
        local backups=("$root/backups/"*-before-*.dump)
        if (( ${#backups[@]} > 7 )); then
            rm -- "${backups[@]:0:${#backups[@]}-7}"
        fi
    fi
    rm -rf -- "$work"
    exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

begin() {
    stage=$1
    printf '%s | %s | %s\n' "$target" "$sha" "$stage" >&3
}

if [[ "$mode" == receive ]]; then
    begin 'receive source'
    cat > "$work/source.tar"
    [[ "$(git get-tar-commit-id < "$work/source.tar")" == "$sha" ]] ||
        die "Source archive commit does not match the requested SHA."
    install -d -m 0755 "$work/source"
    (
        umask 022
        tar --extract --file "$work/source.tar" --directory "$work/source" \
            --no-same-owner --no-same-permissions
    )

    begin 'build image'
    if ! docker image inspect "$APP_IMAGE" >/dev/null 2>&1; then
        docker build --pull --tag "$APP_IMAGE" "$work/source"
    fi
    install -d -m 0755 "$STATIC_DIR"
else
    docker image inspect "$APP_IMAGE" >/dev/null
    [[ -f "$STATIC_DIR/admin/css/base.css" ]] || die "Retained static files are missing."
fi

begin 'start and back up PostgreSQL'
compose up -d --wait --wait-timeout 90 postgres </dev/null
compose exec -T postgres sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    </dev/null > "$work/backup.dump"
compose exec -T postgres pg_restore --list < "$work/backup.dump" >/dev/null
backup_path="$root/backups/$(date -u +%Y%m%dT%H%M%S%N)-before-$sha.dump"
mv -- "$work/backup.dump" "$backup_path"
backup_created=true

begin 'stop application services'
cutover_started=true
compose stop scheduler web </dev/null

if [[ "$mode" == receive ]]; then
    begin 'migrate and collect static files'
    compose run --rm --no-deps -T migrate </dev/null
elif [[ -n "$backup_name" ]]; then
    begin 'restore selected database backup'
    compose exec -T postgres sh -ec '
        pg_restore --exit-on-error --clean --if-exists --create \
            --username "$POSTGRES_USER" --dbname postgres
    ' < "$root/backups/$backup_name"
fi

begin 'start web and scheduler'
point_static_at "$sha"
compose up -d --no-deps --force-recreate web scheduler </dev/null
scheduler=$(compose ps -q scheduler </dev/null)

begin 'verify HTTPS and scheduler'
http_ok() {
    local response
    response=$(curl -qfsS --proto '=https' --max-time 5 --noproxy '*' \
        --resolve "$domain:443:127.0.0.1" -o /dev/null -w '%{http_code}' "https://$domain$1") &&
        [[ "$response" == 200 ]]
}

healthy=false
for _ in {1..24}; do
    sleep 5
    if [[ -n "$scheduler" &&
          "$(docker inspect --format '{{.State.Status}} {{.RestartCount}}' "$scheduler")" == 'running 0' ]] &&
        http_ok /healthz/ && http_ok /static/admin/css/base.css
    then
        healthy=true
        break
    fi
done
[[ "$healthy" == true ]] || die "HTTPS or scheduler did not become healthy."

begin 'record successful release'
if [[ "$sha" != "$current" ]]; then
    previous=$current
fi
printf '%s\n%s\n' "$sha" "$previous" > "$work/successful"
mv -f -- "$work/successful" "$root/successful"
cutover_started=false

# Remove older deployment assets after success. Leave Docker volumes alone.
for path in "$static_root/releases/"*; do
    release=${path##*/}
    if is_sha "$release" && [[ "$release" != "$sha" && "$release" != "$previous" ]]; then
        rm -rf -- "$path" || true
    fi
done
while read -r release; do
    if is_sha "$release" && [[ "$release" != "$sha" && "$release" != "$previous" ]]; then
        docker image rm "$image_repo:$release" || true
    fi
done < <(docker image ls --format '{{.Tag}}' "$image_repo")

printf 'Deployed %s to %s.\n' "$sha" "$target" >&3
