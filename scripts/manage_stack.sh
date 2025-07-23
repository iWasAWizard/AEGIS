#!/bin/bash
# AEGIS/manage_stack.sh
# A simple management script for the entire AEGIS+BEND stack.

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helper Functions ---
print_info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}WARN: $1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

usage() {
    echo "Usage: $0 {up|down|rebuild|pull|status|logs|exec|restart|prune} [service]"
    echo
    echo "Commands:"
    echo "  up                - Start both AEGIS and BEND stacks."
    echo "  down              - Stop both AEGIS and BEND stacks."
    echo "  rebuild [service] - Force rebuild and start stacks (or a specific service)."
    echo "  pull              - Pull the latest versions of any pre-built images."
    echo "  status            - Show the status of all containers in both stacks."
    echo "  logs [service]    - Tail logs from a specific service (e.g., 'agent', 'vllm'). Defaults to 'agent'."
    echo "  exec <service> <cmd> - Execute a command in a running service container (e.g., 'exec agent bash')."
    echo "  restart [service] - Restart all stacks (or a specific service)."
    echo "  prune             - Stop and remove all containers, networks, AND volumes. DANGEROUS."
    exit 1
}

# --- Pre-flight Checks ---
if [ -z "$1" ]; then
    usage
fi

# Define paths relative to the script's execution directory.
AEGIS_DIR=".."
BEND_DIR="../../BEND"

if [ ! -d "${AEGIS_DIR}" ] || [ ! -d "${BEND_DIR}" ]; then
    print_error "Couldn't find the folders!\nMake sure that the 'aegis' and 'BEND' directories are present."
    exit 1
fi

# --- Command Logic ---
COMMAND=$1
SERVICE=$2
shift 2
EXEC_CMD="$@"

AEGIS_SERVICES=("agent")
# Updated list of all BEND services
BEND_SERVICES=("vllm" "redis" "langfuse-server" "langfuse-db" "nemoguardrails" "openwebui" "whisper" "piper" "glances" "qdrant" "retriever" "voiceproxy")

TARGET_DIR=""
if [[ " ${AEGIS_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=${AEGIS_DIR}
elif [[ " ${BEND_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=${BEND_DIR}
fi

case "$COMMAND" in
    up)
        print_info "Starting BEND stack..."
        (cd "${BEND_DIR}" && ./scripts/manage.sh up)

        print_info "Checking for shared Docker network..."
        if ! docker network ls | grep -q "bend_bend-net"; then
            print_error "The 'bend_bend-net' network was not found. Please ensure the BEND stack is running correctly before starting AEGIS."
            exit 1
        fi
        print_success "Shared network found."

        print_info "Starting AEGIS stack..."
        # Source the .env file to pass all variables to the docker compose command
        if [ -f "${AEGIS_DIR}/.env" ]; then
            set -a # Automatically export all variables
            source "${AEGIS_DIR}/.env"
            set +a
            (cd "${AEGIS_DIR}" && docker compose up --build -d)
        else
            print_warn "AEGIS .env file not found. Starting without it."
            (cd "${AEGIS_DIR}" && docker compose up --build -d)
        fi

        print_success "All stacks started."
        print_info "Cleaning up old images..."
        docker image prune -f
        ;;

    down)
        print_info "Stopping AEGIS stack..."
        (cd "${AEGIS_DIR}" && docker compose down)
        print_info "Stopping BEND stack..."
        (cd "${BEND_DIR}" && ./scripts/manage.sh down)
        print_success "All stacks stopped."
        ;;

    rebuild)
        print_info "Force rebuilding images..."
        if [ -n "${SERVICE}" ]; then
            if [ -z "${TARGET_DIR}" ]; then
                print_error "Unknown service '$SERVICE'."
                exit 1
            fi
            print_info "Rebuilding service: ${SERVICE}"
            (cd "${TARGET_DIR}" && docker compose build --no-cache "${SERVICE}")
            print_info "Restarting service: ${SERVICE}"
            (cd "${TARGET_DIR}" && docker compose up -d --force-recreate "${SERVICE}")
        else
            print_info "Rebuilding BEND stack..."
            (cd "${BEND_DIR}" && ./scripts/manage.sh rebuild)
            print_info "Rebuilding AEGIS stack..."
            (cd "${AEGIS_DIR}" && docker compose build --no-cache)
            (cd "${AEGIS_DIR}" && docker compose up -d --force-recreate)
        fi
        print_success "Rebuild and restart complete."
        print_info "Cleaning up old images..."
        docker image prune -f
        ;;

    pull)
        print_info "Pulling latest images for BEND stack..."
        (cd "${BEND_DIR}" && docker compose pull)
        print_info "Pulling latest images for AEGIS stack..."
        (cd "${AEGIS_DIR}" && docker compose pull)
        print_success "Image pull complete."
        ;;

    status)
        print_info "--- BEND Stack Status ---"
        (cd "${BEND_DIR}" && ./scripts/manage.sh status)
        echo ""
        print_info "--- AEGIS Stack Status ---"
        (cd "${AEGIS_DIR}" && docker compose ps)
        ;;

    logs)
        SERVICE=${SERVICE:-"agent"} # Default to agent logs
        print_info "Tailing logs for service: '$SERVICE'... (Ctrl+C to exit)"

        # Determine target directory based on service name
        if [[ " ${AEGIS_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
            TARGET_DIR=${AEGIS_DIR}
        elif [[ " ${BEND_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
            TARGET_DIR=${BEND_DIR}
        else
             print_error "Unknown service '$SERVICE'."
             exit 1
        fi
        (cd "$TARGET_DIR" && docker compose logs -f "$SERVICE")
        ;;

    exec)
        if [ -z "$SERVICE" ] || [ -z "$EXEC_CMD" ]; then
            print_error "Usage: $0 exec <service> <command>"
            exit 1
        fi
        if [ -z "$TARGET_DIR" ]; then
            print_error "Unknown service '$SERVICE'."
            exit 1
        fi
        print_info "Executing '$EXEC_CMD' in service '$SERVICE'..."
        (cd "$TARGET_DIR" && docker compose exec "$SERVICE" bash -c "$EXEC_CMD")
        ;;

    restart)
        print_info "Restarting stacks..."
        if [ -n "$SERVICE" ]; then
             if [ -z "$TARGET_DIR" ]; then
                print_error "Unknown service '$SERVICE'."
                exit 1
            fi
             (cd "$TARGET_DIR" && docker compose restart "$SERVICE")
        else
            (cd "${AEGIS_DIR}" && docker compose restart)
            (cd "${BEND_DIR}" && ./scripts/manage.sh restart)
        fi
        print_success "Restart complete."
        ;;

    prune)
        print_warn "This will stop and remove all containers, networks, and VOLUMES."
        read -p "Are you sure you want to permanently delete all data? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Pruning AEGIS stack..."
            (cd "${AEGIS_DIR}" && docker compose down -v)
            print_info "Pruning BEND stack..."
            (cd "${BEND_DIR}" && ./scripts/manage.sh down -v)
            print_success "All stacks and data have been pruned."
        else
            print_info "Prune operation cancelled."
        fi
        ;;

    *)
        usage
        ;;
esac