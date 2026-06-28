#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu VPS: install git & Docker, deploy flask-weather, start via Compose.
#
# Usage (on VPS as root):
#   curl -fsSL https://raw.githubusercontent.com/sigmaray/flask-weather/main/scripts/setup-vps.sh | bash
#   # or
#   sudo bash scripts/setup-vps.sh
#   sudo bash scripts/setup-vps.sh --swap
#
# Environment variables:
#   DEPLOY_DIR                  Target directory (default: ~/r/d/flask-weather)
#   REPO_URL                    Git clone URL (default: https://github.com/sigmaray/flask-weather.git)
#   GIT_REF                     Branch, tag, or commit to deploy (default: main)
#   DATABASE_URL                PostgreSQL on the host (default: postgres@host.docker.internal:5432/weather)
#   SECRET_KEY                  Flask secret key (default: auto-generated and saved in DEPLOY_DIR/.env)
#   SETUP_SKIP_APT              Set to 1 to skip apt-get (useful in CI where git is preinstalled)
#   SETUP_SKIP_DOCKER_INSTALL   Set to 1 to skip Docker installation (useful in CI)
#   SETUP_SKIP_PG_CHECK         Set to 1 to skip PostgreSQL reachability check
#   SETUP_SOURCE_DIR            Copy project from this path instead of cloning (CI / local test)
#   SETUP_ALLOW_NON_ROOT        Set to 1 to skip root check (CI with passwordless sudo)
#   SETUP_FORCE                 Set to 1 to redeploy even when already at GIT_REF and running
#   SETUP_SWAP                  Set to 1 to configure swap (same as --swap)
#   SETUP_SWAP_SIZE_MB          Swap file size in megabytes (default: 2048)
#   SETUP_SWAP_FILE             Swap file path (default: /swapfile)
#   HEALTH_URL                  URL for readiness probe (default: http://127.0.0.1:5000/health)
#   HEALTH_TIMEOUT_SEC          Seconds to wait for the app (default: 120)

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-${HOME}/r/d/flask-weather}"
REPO_URL="${REPO_URL:-https://github.com/sigmaray/flask-weather.git}"
GIT_REF="${GIT_REF:-main}"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@host.docker.internal:5432/weather}"
SETUP_SKIP_APT="${SETUP_SKIP_APT:-0}"
SETUP_SKIP_DOCKER_INSTALL="${SETUP_SKIP_DOCKER_INSTALL:-0}"
SETUP_SKIP_PG_CHECK="${SETUP_SKIP_PG_CHECK:-0}"
SETUP_SOURCE_DIR="${SETUP_SOURCE_DIR:-}"
SETUP_ALLOW_NON_ROOT="${SETUP_ALLOW_NON_ROOT:-0}"
SETUP_FORCE="${SETUP_FORCE:-0}"
SETUP_SWAP="${SETUP_SWAP:-0}"
SETUP_SWAP_SIZE_MB="${SETUP_SWAP_SIZE_MB:-2048}"
SETUP_SWAP_FILE="${SETUP_SWAP_FILE:-/swapfile}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5000/health}"
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-120}"

DEPLOY_ENV_FILE="${DEPLOY_DIR}/.env"

log() {
  printf '[setup-vps] %s\n' "$*" >&2
}

die() {
  printf '[setup-vps] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: setup-vps.sh [--swap]

Bootstrap Ubuntu, install git and Docker, deploy flask-weather, and start docker compose.

Options:
  --swap                      Create and enable a swap file if swap is not configured

Environment variables:
  DEPLOY_DIR                  Deployment directory (default: ~/r/d/flask-weather)
  REPO_URL                    Git repository URL
  GIT_REF                     Branch, tag, or commit (default: main)
  DATABASE_URL                Host PostgreSQL URL (default: postgres@host.docker.internal:5432/weather)
  SECRET_KEY                  Flask session secret (saved to DEPLOY_DIR/.env when unset)
  SETUP_SKIP_APT              Skip apt-get when set to 1
  SETUP_SKIP_DOCKER_INSTALL   Skip Docker install when set to 1
  SETUP_SKIP_PG_CHECK         Skip PostgreSQL reachability check when set to 1
  SETUP_SOURCE_DIR            Use existing directory instead of git clone
  SETUP_ALLOW_NON_ROOT        Allow running without root (for CI)
  SETUP_FORCE                 Redeploy even when already at GIT_REF and running
  SETUP_SWAP                  Configure swap when set to 1 (same as --swap)
  SETUP_SWAP_SIZE_MB          Swap file size in megabytes (default: 2048)
  SETUP_SWAP_FILE             Swap file path (default: /swapfile)
  HEALTH_URL                  Readiness check URL
  HEALTH_TIMEOUT_SEC          Readiness timeout in seconds
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --swap)
        SETUP_SWAP=1
        shift
        ;;
      *)
        die "Unknown option: $1 (try --help)"
        ;;
    esac
  done
}

require_root() {
  if [[ "${SETUP_ALLOW_NON_ROOT}" == "1" ]]; then
    return 0
  fi
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Run as root: sudo bash $0"
  fi
}

read_env_value() {
  local key="$1"
  local file="$2"
  [[ -f "${file}" ]] || return 1
  grep -E "^${key}=" "${file}" | tail -1 | cut -d= -f2-
}

ensure_deploy_env() {
  [[ -d "${DEPLOY_DIR}" ]] || die "Deploy directory missing: ${DEPLOY_DIR}"

  local existing_secret=""
  existing_secret="$(read_env_value SECRET_KEY "${DEPLOY_ENV_FILE}" 2>/dev/null || true)"

  if [[ -z "${SECRET_KEY:-}" ]]; then
    if [[ -n "${existing_secret}" ]]; then
      SECRET_KEY="${existing_secret}"
      log "Using SECRET_KEY from ${DEPLOY_ENV_FILE}"
    elif command -v openssl >/dev/null 2>&1; then
      SECRET_KEY="$(openssl rand -hex 32)"
      log "Generated new SECRET_KEY"
    else
      SECRET_KEY="dev-secret-change-in-production"
      log "openssl not found; using default SECRET_KEY — change it in production"
    fi
  fi
  export SECRET_KEY

  local tmp
  tmp="$(mktemp)"
  chmod 600 "${tmp}"
  {
    printf 'DATABASE_URL=%s\n' "${DATABASE_URL}"
    printf 'SECRET_KEY=%s\n' "${SECRET_KEY}"
  } > "${tmp}"
  mv "${tmp}" "${DEPLOY_ENV_FILE}"
  chmod 600 "${DEPLOY_ENV_FILE}"
  log "Wrote ${DEPLOY_ENV_FILE}"
}

parse_database_url() {
  local url="$1"
  if [[ "${url}" =~ postgres(ql)?://([^:@/]+):([^@/]*)@([^:/]+):([0-9]+)/([^?]+) ]]; then
    PG_USER="${BASH_REMATCH[2]}"
    PG_PASS="${BASH_REMATCH[3]}"
    PG_HOST="${BASH_REMATCH[4]}"
    PG_PORT="${BASH_REMATCH[5]}"
    PG_DB="${BASH_REMATCH[6]}"
  else
    die "Cannot parse DATABASE_URL: ${url}"
  fi

  if [[ "${PG_HOST}" == "host.docker.internal" ]]; then
    PG_CHECK_HOST="127.0.0.1"
  else
    PG_CHECK_HOST="${PG_HOST}"
  fi
}

check_postgres() {
  if [[ "${SETUP_SKIP_PG_CHECK}" == "1" ]]; then
    log "Skipping PostgreSQL check (SETUP_SKIP_PG_CHECK=1)"
    return 0
  fi

  parse_database_url "${DATABASE_URL}"
  log "Checking PostgreSQL at ${PG_CHECK_HOST}:${PG_PORT} (database: ${PG_DB})..."

  if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h "${PG_CHECK_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -t 5 -q 2>/dev/null; then
      log "PostgreSQL is reachable"
      return 0
    fi
  elif command -v nc >/dev/null 2>&1; then
    if nc -z -w 5 "${PG_CHECK_HOST}" "${PG_PORT}" 2>/dev/null; then
      log "PostgreSQL port is open (install postgresql-client for a stronger check)"
      return 0
    fi
  elif timeout 5 bash -c "echo >/dev/tcp/${PG_CHECK_HOST}/${PG_PORT}" 2>/dev/null; then
    log "PostgreSQL port is open"
    return 0
  fi

  die "PostgreSQL is not reachable at ${PG_CHECK_HOST}:${PG_PORT}. Install and configure PostgreSQL on the host (user/db from DATABASE_URL) before running this script."
}

install_packages() {
  if [[ "${SETUP_SKIP_APT}" == "1" ]]; then
    command -v git >/dev/null 2>&1 || die "git not found (install it or unset SETUP_SKIP_APT)"
    command -v curl >/dev/null 2>&1 || die "curl not found (install it or unset SETUP_SKIP_APT)"
    command -v rsync >/dev/null 2>&1 || die "rsync not found (install it or unset SETUP_SKIP_APT)"
    log "Skipping apt-get (SETUP_SKIP_APT=1)"
    return 0
  fi

  log "Installing git and prerequisites..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git curl ca-certificates openssl rsync postgresql-client
}

install_etckeeper() {
  if [[ "${SETUP_SKIP_APT}" == "1" ]]; then
    return 0
  fi

  if command -v etckeeper >/dev/null 2>&1; then
    log "etckeeper is already installed"
    return 0
  fi

  log "Installing etckeeper..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq etckeeper
}

install_docker() {
  if [[ "${SETUP_SKIP_DOCKER_INSTALL}" == "1" ]]; then
    log "Skipping Docker installation (SETUP_SKIP_DOCKER_INSTALL=1)"
    command -v docker >/dev/null 2>&1 || die "docker not found and installation was skipped"
    docker compose version >/dev/null 2>&1 || die "docker compose plugin not found"
    return 0
  fi

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker is already installed"
    return 0
  fi

  log "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
}

swap_is_configured() {
  local swap_kb
  swap_kb="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
  [[ "${swap_kb:-0}" -gt 0 ]]
}

ensure_swap_in_fstab() {
  local swap_file="$1"
  if grep -qF "${swap_file}" /etc/fstab 2>/dev/null; then
    return 0
  fi
  echo "${swap_file} none swap sw 0 0" >> /etc/fstab
}

setup_swap() {
  if [[ "${SETUP_SWAP}" != "1" ]]; then
    return 0
  fi

  if swap_is_configured; then
    log "Swap is already configured — skipping"
    swapon --show >&2 || true
    return 0
  fi

  local swap_file="${SETUP_SWAP_FILE}"
  local swap_mb="${SETUP_SWAP_SIZE_MB}"

  log "Configuring ${swap_mb}MB swap at ${swap_file}..."

  if [[ -f "${swap_file}" ]]; then
    log "Swap file ${swap_file} exists — enabling it"
  elif ! fallocate -l "${swap_mb}M" "${swap_file}" 2>/dev/null; then
    log "fallocate failed; creating swap file with dd (this may take a while)..."
    dd if=/dev/zero of="${swap_file}" bs=1M count="${swap_mb}" status=none
  fi

  chmod 600 "${swap_file}"
  mkswap "${swap_file}" >/dev/null
  swapon "${swap_file}"
  ensure_swap_in_fstab "${swap_file}"

  log "Swap enabled:"
  swapon --show >&2 || true
}

fetch_existing_clone() {
  if git -C "${DEPLOY_DIR}" fetch --depth 1 origin "${GIT_REF}" 2>/dev/null; then
    return 0
  fi
  git -C "${DEPLOY_DIR}" fetch --depth 1 origin "refs/tags/${GIT_REF}:refs/tags/${GIT_REF}"
}

remote_ref_sha() {
  git -C "${DEPLOY_DIR}" rev-parse FETCH_HEAD 2>/dev/null \
    || git -C "${DEPLOY_DIR}" rev-parse "refs/tags/${GIT_REF}" 2>/dev/null \
    || git -C "${DEPLOY_DIR}" rev-parse "origin/${GIT_REF}" 2>/dev/null \
    || git -C "${DEPLOY_DIR}" rev-parse "${GIT_REF}"
}

project_worktree_clean() {
  git -C "${DEPLOY_DIR}" diff --quiet HEAD \
    && git -C "${DEPLOY_DIR}" diff --cached --quiet HEAD
}

reset_existing_clone() {
  local target_sha
  target_sha="$(remote_ref_sha)"
  git -C "${DEPLOY_DIR}" checkout --detach "${target_sha}"
  git -C "${DEPLOY_DIR}" reset --hard "${target_sha}"
}

clone_project() {
  mkdir -p "$(dirname "${DEPLOY_DIR}")"
  if git clone --branch "${GIT_REF}" --depth 1 "${REPO_URL}" "${DEPLOY_DIR}" 2>/dev/null; then
    return 0
  fi

  log "Shallow branch clone failed; fetching ${GIT_REF} by ref..."
  git clone --depth 1 "${REPO_URL}" "${DEPLOY_DIR}"
  fetch_existing_clone
  local target_sha
  target_sha="$(remote_ref_sha)"
  git -C "${DEPLOY_DIR}" checkout --detach "${target_sha}"
}

deploy_from_source() {
  [[ -d "${SETUP_SOURCE_DIR}" ]] || die "SETUP_SOURCE_DIR does not exist: ${SETUP_SOURCE_DIR}"
  mkdir -p "${DEPLOY_DIR}"

  local rsync_opts=(-a --delete --exclude '.env')
  local changes
  changes="$(rsync "${rsync_opts[@]}" --dry-run --itemize-changes "${SETUP_SOURCE_DIR}/" "${DEPLOY_DIR}/" | wc -l)"
  if [[ "${changes}" -eq 0 ]]; then
    log "Source tree already synced to ${DEPLOY_DIR}"
    printf 'current'
    return 0
  fi

  rsync "${rsync_opts[@]}" "${SETUP_SOURCE_DIR}/" "${DEPLOY_DIR}/"
  printf 'sync'
}

compose_stack_running() {
  [[ -d "${DEPLOY_DIR}" ]] || return 1

  local services
  services="$(cd "${DEPLOY_DIR}" && docker compose ps --status running --format '{{.Service}}' 2>/dev/null)" \
    || return 1
  grep -qx 'web' <<<"${services}" || return 1
}

app_is_ready() {
  curl -sf "${HEALTH_URL}" >/dev/null
}

# Echoes "sync" when the working tree must be updated, "current" when already at GIT_REF.
assess_existing_clone() {
  fetch_existing_clone

  local local_sha remote_sha
  local_sha="$(git -C "${DEPLOY_DIR}" rev-parse HEAD)"
  remote_sha="$(remote_ref_sha)"

  if [[ "${local_sha}" == "${remote_sha}" ]] && project_worktree_clean; then
    log "Already at ${GIT_REF} (${local_sha:0:7}) in ${DEPLOY_DIR}"
    printf 'current'
    return 0
  fi

  if [[ "${local_sha}" != "${remote_sha}" ]]; then
    log "Updating ${local_sha:0:7} -> ${remote_sha:0:7} in ${DEPLOY_DIR}"
  else
    log "Resetting local changes in ${DEPLOY_DIR}"
  fi
  reset_existing_clone
  printf 'sync'
}

deploy_project() {
  log "Deploying project to ${DEPLOY_DIR}..."

  if [[ -n "${SETUP_SOURCE_DIR}" ]]; then
    deploy_from_source
    return 0
  fi

  if [[ -d "${DEPLOY_DIR}/.git" ]]; then
    assess_existing_clone
    return 0
  fi

  if [[ -d "${DEPLOY_DIR}" ]] && [[ -n "$(ls -A "${DEPLOY_DIR}" 2>/dev/null)" ]]; then
    die "${DEPLOY_DIR} exists but is not a git repository. Remove or rename it, then re-run."
  fi

  if [[ -d "${DEPLOY_DIR}" ]]; then
    rmdir "${DEPLOY_DIR}" 2>/dev/null \
      || die "${DEPLOY_DIR} exists but is not a git repository and is not empty."
  fi

  clone_project
  printf 'sync'
}

start_compose() {
  local rebuild="${1:-1}"

  if [[ "${rebuild}" == "1" ]]; then
    log "Building and starting docker compose stack..."
    cd "${DEPLOY_DIR}"
    docker compose up -d --build
    return 0
  fi

  log "Starting docker compose stack (no rebuild)..."
  cd "${DEPLOY_DIR}"
  docker compose up -d
}

wait_for_app() {
  log "Waiting for app at ${HEALTH_URL} (timeout: ${HEALTH_TIMEOUT_SEC}s)..."
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SEC))
  while (( SECONDS < deadline )); do
    if curl -sf "${HEALTH_URL}" >/dev/null; then
      log "Application is ready"
      return 0
    fi
    sleep 2
  done

  log "Application failed to become ready; recent logs:"
  cd "${DEPLOY_DIR}"
  docker compose logs --tail=50 || true
  die "Health check failed: ${HEALTH_URL}"
}

main() {
  parse_args "$@"

  require_root
  setup_swap
  install_packages
  install_etckeeper
  install_docker

  local deploy_action
  deploy_action="$(deploy_project)"

  ensure_deploy_env
  check_postgres

  if [[ "${SETUP_FORCE}" == "1" ]]; then
    log "SETUP_FORCE=1 — rebuilding and restarting the stack"
    start_compose 1
    wait_for_app
  elif [[ "${deploy_action}" == "current" \
        && compose_stack_running \
        && app_is_ready ]]; then
    log "Project is already deployed at ${GIT_REF} and the stack is healthy — skipping redeploy"
    log "Use SETUP_FORCE=1 to rebuild and restart anyway"
  elif [[ "${deploy_action}" == "current" ]]; then
    log "Project is already at ${GIT_REF}; ensuring compose stack is up"
    start_compose 0
    wait_for_app
  else
    start_compose 1
    wait_for_app
  fi

  log "Deployment complete."
  log "  Directory: ${DEPLOY_DIR}"
  log "  URL:       http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1'):5000"
  log "  Next step: create a user with:"
  log "    cd ${DEPLOY_DIR} && docker compose exec web flask users-create"
}

main "$@"
