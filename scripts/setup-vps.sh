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
#   DEPLOY_DIR                  Target directory (default: /opt/flask-weather)
#   REPO_URL                    Git clone URL (default: https://github.com/sigmaray/flask-weather.git)
#   GIT_REF                     Branch, tag, or commit to deploy (default: main)
#   DATABASE_URL                PostgreSQL on the host (default: weather@host.docker.internal:5432/weather)
#   SECRET_KEY                  Flask secret key (default: auto-generated on VPS)
#   SETUP_SKIP_APT              Set to 1 to skip apt-get (useful in CI where git is preinstalled)
#   SETUP_SKIP_DOCKER_INSTALL   Set to 1 to skip Docker installation (useful in CI)
#   SETUP_SOURCE_DIR            Copy project from this path instead of cloning (CI / local test)
#   SETUP_ALLOW_NON_ROOT        Set to 1 to skip root check (CI with passwordless sudo)
#   SETUP_FORCE                 Set to 1 to redeploy even when already at GIT_REF and running
#   SETUP_SWAP                  Set to 1 to configure swap (same as --swap)
#   SETUP_SWAP_SIZE_MB          Swap file size in megabytes (default: 2048)
#   SETUP_SWAP_FILE             Swap file path (default: /swapfile)
#   HEALTH_URL                  URL for readiness probe (default: http://127.0.0.1:5000/auth/login)
#   HEALTH_TIMEOUT_SEC          Seconds to wait for the app (default: 120)

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/flask-weather}"
REPO_URL="${REPO_URL:-https://github.com/sigmaray/flask-weather.git}"
GIT_REF="${GIT_REF:-main}"
DATABASE_URL="${DATABASE_URL:-postgresql://weather:weather@host.docker.internal:5432/weather}"
SETUP_SKIP_APT="${SETUP_SKIP_APT:-0}"
SETUP_SKIP_DOCKER_INSTALL="${SETUP_SKIP_DOCKER_INSTALL:-0}"
SETUP_SOURCE_DIR="${SETUP_SOURCE_DIR:-}"
SETUP_ALLOW_NON_ROOT="${SETUP_ALLOW_NON_ROOT:-0}"
SETUP_FORCE="${SETUP_FORCE:-0}"
SETUP_SWAP="${SETUP_SWAP:-0}"
SETUP_SWAP_SIZE_MB="${SETUP_SWAP_SIZE_MB:-2048}"
SETUP_SWAP_FILE="${SETUP_SWAP_FILE:-/swapfile}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5000/auth/login}"
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-120}"

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
  DEPLOY_DIR                  Deployment directory (default: /opt/flask-weather)
  REPO_URL                    Git repository URL
  GIT_REF                     Branch, tag, or commit (default: main)
  DATABASE_URL                Host PostgreSQL URL (default: weather@host.docker.internal:5432/weather)
  SECRET_KEY                  Flask session secret (random if unset on VPS)
  SETUP_SKIP_APT              Skip apt-get when set to 1
  SETUP_SKIP_DOCKER_INSTALL   Skip Docker install when set to 1
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

ensure_secret_key() {
  if [[ -z "${SECRET_KEY:-}" ]]; then
    if command -v openssl >/dev/null 2>&1; then
      SECRET_KEY="$(openssl rand -hex 32)"
    else
      SECRET_KEY="dev-secret-change-in-production"
      log "openssl not found; using default SECRET_KEY — change it in production"
    fi
  fi
  export SECRET_KEY
}

install_packages() {
  if [[ "${SETUP_SKIP_APT}" == "1" ]]; then
    command -v git >/dev/null 2>&1 || die "git not found (install it or unset SETUP_SKIP_APT)"
    command -v curl >/dev/null 2>&1 || die "curl not found (install it or unset SETUP_SKIP_APT)"
    log "Skipping apt-get (SETUP_SKIP_APT=1)"
    return 0
  fi

  log "Installing git and prerequisites..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git curl ca-certificates openssl
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
  if grep -q "[[:space:]]${swap_file}[[:space:]]" /etc/fstab 2>/dev/null; then
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

remote_ref_sha() {
  git -C "${DEPLOY_DIR}" rev-parse "origin/${GIT_REF}" 2>/dev/null \
    || git -C "${DEPLOY_DIR}" rev-parse "${GIT_REF}"
}

project_worktree_clean() {
  git -C "${DEPLOY_DIR}" diff --quiet HEAD \
    && git -C "${DEPLOY_DIR}" diff --cached --quiet HEAD
}

fetch_existing_clone() {
  git -C "${DEPLOY_DIR}" fetch --depth 1 origin "${GIT_REF}"
}

reset_existing_clone() {
  git -C "${DEPLOY_DIR}" checkout "${GIT_REF}"
  git -C "${DEPLOY_DIR}" reset --hard "origin/${GIT_REF}" 2>/dev/null \
    || git -C "${DEPLOY_DIR}" reset --hard "${GIT_REF}"
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
    [[ -d "${SETUP_SOURCE_DIR}" ]] || die "SETUP_SOURCE_DIR does not exist: ${SETUP_SOURCE_DIR}"
    rm -rf "${DEPLOY_DIR}"
    mkdir -p "${DEPLOY_DIR}"
    cp -a "${SETUP_SOURCE_DIR}/." "${DEPLOY_DIR}/"
    printf 'sync'
    return 0
  fi

  if [[ -d "${DEPLOY_DIR}/.git" ]]; then
    assess_existing_clone
    return 0
  fi

  mkdir -p "$(dirname "${DEPLOY_DIR}")"
  git clone --branch "${GIT_REF}" --depth 1 "${REPO_URL}" "${DEPLOY_DIR}"
  printf 'sync'
}

start_compose() {
  local rebuild="${1:-1}"

  export DATABASE_URL

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
  docker compose logs --tail=50 || true
  die "Health check failed: ${HEALTH_URL}"
}

main() {
  parse_args "$@"

  require_root
  ensure_secret_key
  setup_swap
  install_packages
  install_docker

  local deploy_action
  deploy_action="$(deploy_project)"

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
