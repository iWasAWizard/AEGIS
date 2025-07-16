#!/bin/bash

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
    echo "Usage: $0 {up|down|rebuild|pull|status|logs|exec|restart|prune}"
    echo
    echo "Commands:"
    echo "  up                - Start both AEGIS and BEND stacks."
    echo "  down              - Stop both AEGIS and BEND stacks."
    echo "  rebuild [service] - Force rebuild and start stacks (or a specific service)."
    echo "  pull              - Pull the latest versions of any pre-built images."
    echo "  status            - Show the status of all containers in both stacks."
    echo "  logs [service]    - Tail logs from a specific service (e.g., 'agent', 'koboldcpp'). Defaults to 'agent'."
    echo "  exec <service> <cmd> - Execute a command in a running service container (e.g., 'exec agent bash')."
    echo "  restart [service] - Restart all stacks (or a specific service)."
    echo "  prune             - Stop and remove all containers, networks, AND volumes. DANGEROUS."
    exit 1
}

# --- Pre-flight Checks ---
if [ -z "$1" ]; then
    usage
fi

AEGIS_DIR="./aegis"
BEND_DIR="../BEND"

if [ ! -d "$AEGIS_DIR" ] || [ ! -d "$BEND_DIR" ]; then
    print_error "Couldn't find the folders!\nMake sure that the 'AEGIS' and 'BEND' directories\nare at the same directory level!"
    exit 1
fi

# --- Command Logic ---
COMMAND=$1
SERVICE=$2
shift 2
EXEC_CMD="$@"

AEGIS_SERVICES=("agent")
BEND_SERVICES=("koboldcpp" "openwebui" "whisper" "piper" "glances" "qdrant" "retriever" "voiceproxy")

TARGET_DIR=""
if [[ " ${AEGIS_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=$AEGIS_DIR
elif [[ " ${BEND_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=$BEND_DIR
fi

case "$COMMAND" in
    up)
        print_info "Starting BEND stack..."
        (cd "$BEND_DIR" && ./scripts/manage.sh up)
        print_info "Starting AEGIS stack..."
        (cd "$AEGIS_DIR" && docker compose up --build -d)
        print_success "All stacks started."
        ;;

    down)
        print_info "Stopping AEGIS stack..."
        (cd "$AEGIS_DIR" && docker compose down)
        (cd "$BEND_DIR" && ./scripts/manage.sh down)
        print_success "All stacks stopped."
        ;;

    rebuild)
        print_info "Force rebuilding images..."
        if [ -n "$SERVICE" ]; then
            print_info "Rebuilding service: $SERVICE"
            (cd "$TARGET_DIR" && docker compose build --no-cache "$SERVICE")
            print_info "Restarting service: $SERVICE"
            (cd "$TARGET_DIR" && docker compose up -d --force-recreate "$SERVICE")
        else
            print_info "Rebuilding BEND stack..."
            (cd "$BEND_DIR" && docker compose build --no-cache)
            (cd "$BEND_DIR" && docker compose up -d --force-recreate)
            print_info "Rebuilding AEGIS stack..."
            (cd "$AEGIS_DIR" && docker compose build --no-cache)
            (cd "$AEGIS_DIR" && docker compose up -d --force-recreate)
        fi
        print_success "Rebuild and restart complete."
        ;;

    pull)
        print_info "Pulling latest images for BEND stack..."
        (cd "$BEND_DIR" && docker compose pull)
        print_info "Pulling latest images for AEGIS stack..."
        (cd "$AEGIS_DIR" && docker compose pull)
        print_success "Image pull complete."
        ;;

    status)
        (cd "$BEND_DIR" && ./scripts/manage.sh status)
        echo ""
        print_info "--- AEGIS Stack Status ---"
        (cd "$AEGIS_DIR" && docker compose ps)
        ;;

    logs)
        SERVICE=${SERVICE:-"agent"} # Default to agent logs
        print_info "Tailing logs for service: '$SERVICE'... (Ctrl+C to exit)"
        if [ -z "$TARGET_DIR" ] && [ "$SERVICE" != "agent" ]; then
            TARGET_DIR=$BEND_DIR # Assume it's a BEND service if not AEGIS
        elif [ -z "$TARGET_DIR" ]; then
             TARGET_DIR=$AEGIS_DIR
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
             (cd "$TARGET_DIR" && docker compose restart "$SERVICE")
        else
            (cd "$AEGIS_DIR" && docker compose restart)
            (cd "$BEND_DIR" && docker compose restart)
        fi
        print_success "Restart complete."
        ;;

    prune)
        print_warn "This will stop and remove all containers, networks, and VOLUMES."
        read -p "Are you sure you want to permanently delete all data? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Pruning AEGIS stack..."
            (cd "$AEGIS_DIR" && docker compose down -v)
            print_info "Pruning BEND stack..."
            (cd "$BEND_DIR" && ./scripts/manage.sh down -v) # Assuming BEND manage script supports -v
            print_success "All stacks and data have been pruned."
        else
            print_info "Prune operation cancelled."
        fi
        ;;

    *)
        usage
        ;;
esac
