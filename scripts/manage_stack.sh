#!/bin/bash
# AEGIS/manage_stack.sh
# A simple management script for the entire AEGIS+BEND stack.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

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
    echo "Usage: $0 {up|down|rebuild|pull|status|logs|exec|restart|prune} [options] [service] [command...]"
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
    echo
    echo "Options:"
    echo "  --gpu             - Pass the --gpu flag to the BEND stack."
    echo "  --lite [profile]  - Use the lite configuration for BEND. Optionally specify a profile ('vllm' or 'ollama')."
    echo "                    If no profile is given, both LLM backends are started."
    echo
    echo "Examples:"
    echo "  ./manage_stack.sh up --gpu"
    echo "  ./manage_stack.sh up --lite vllm --gpu"
    echo "  ./manage_stack.sh up --lite"
    exit 1
}

# --- Pre-flight Checks ---
if [ -z "$1" ]; then
    usage
fi

# Define paths relative to the script's execution directory.
AEGIS_DIR="${SCRIPT_DIR}/.."
BEND_DIR="${SCRIPT_DIR}/../../BEND"

if [ ! -d "${AEGIS_DIR}" ] || [ ! -d "${BEND_DIR}" ]; then
    print_error "Couldn't find the folders!\nMake sure that the 'aegis' and 'BEND' directories are present."
    exit 1
fi

# --- Argument Parsing ---
COMMAND=$1
shift # The first argument is the command

# Parse remaining arguments for flags and service names
LITE_ARGS=""
GPU_ARGS=""
SERVICE=""
EXEC_CMD=""
OTHER_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lite)
      if [[ -n "$2" && ("$2" == "vllm" || "$2" == "ollama") ]]; then
        LITE_ARGS="--lite $2"
        shift 2
      else
        LITE_ARGS="--lite"
        shift
      fi
      ;;
    --gpu)
      GPU_ARGS="--gpu"
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      OTHER_ARGS+=("$1")
      shift
      ;;
  esac
done

# The first non-flag argument is the service, the rest is the exec command
if [ ${#OTHER_ARGS[@]} -gt 0 ]; then
    SERVICE=${OTHER_ARGS[0]}
    EXEC_CMD="${OTHER_ARGS[@]:1}"
fi


# --- Command Logic ---
AEGIS_SERVICES=("agent")
BEND_SERVICES=("vllm" "redis" "nemoguardrails" "openwebui" "whisper" "piper" "glances" "qdrant" "retriever" "voiceproxy" "ollama")

TARGET_DIR=""
if [[ " ${AEGIS_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=${AEGIS_DIR}
elif [[ " ${BEND_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    TARGET_DIR=${BEND_DIR}
fi


case "$COMMAND" in
    up)
        print_info "Starting BEND stack..."
        # Dynamically construct and execute the BEND manage command
        BEND_CMD_ARGS="up $LITE_ARGS $GPU_ARGS"
        (cd "${BEND_DIR}" && ./scripts/manage.sh ${BEND_CMD_ARGS})
        print_success "BEND stack started."

        print_info "Checking for shared Docker network..."
        # Source the .env file to get the network name
        if [ -f "${AEGIS_DIR}/.env" ]; then
            set -a
            source "${AEGIS_DIR}/.env"
            set +a
        fi

        # Use the variable from the .env file, with a default
        NETWORK_NAME=${AEGIS_EXTERNAL_NETWORK:-bend_bend-net}

        if ! docker network ls | grep -q "$NETWORK_NAME"; then
            print_error "The '${NETWORK_NAME}' network was not found. Please ensure the backend stack is running correctly before starting AEGIS."
            exit 1
        fi
        print_success "Shared network '$NETWORK_NAME' found."

        print_info "Starting AEGIS stack..."
        (cd "${AEGIS_DIR}" && docker compose up --build -d)

        print_success "All stacks started."
        print_info "Cleaning up old images..."
        docker image prune -f
        ;;

    down)
        print_info "Stopping AEGIS stack..."
        (cd "${AEGIS_DIR}" && docker compose down)
        print_info "Stopping BEND stack..."
        # The down command in BEND is smart enough to handle all configs
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
            (cd "${BEND_DIR}" && ./scripts/manage.sh rebuild $GPU_ARGS) # Pass GPU flag to BEND rebuild
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
        (cd "${BEND_DIR}" && ./scripts/manage.sh pull)
        print_info "Pulling latest images for AEGIS stack..."
        (cd "${AEGIS_DIR}" && docker compose pull)
        print_success "Image pull complete."
        ;;

    status)
        print_info "--- BEND Stack Status ---"
        (cd "${BEND_DIR}" && ./scripts/manage.sh status $LITE_ARGS $GPU_ARGS)
        echo ""
        print_info "--- AEGIS Stack Status ---"
        (cd "${AEGIS_DIR}" && docker compose ps)
        ;;

    logs)
        SERVICE=${SERVICE:-"agent"} # Default to agent logs
        print_info "Tailing logs for service: '$SERVICE'... (Ctrl+C to exit)"

        # Determine target directory based on service name
        if [[ " ${AEGIS_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
            (cd "$AEGIS_DIR" && docker compose logs -f "$SERVICE")
        elif [[ " ${BEND_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
            (cd "$BEND_DIR" && ./scripts/manage.sh logs $LITE_ARGS $GPU_ARGS "$SERVICE")
        else
             print_error "Unknown service '$SERVICE'."
             exit 1
        fi
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
             if [ -z "${TARGET_DIR}" ]; then
                print_error "Unknown service '$SERVICE'."
                exit 1
            fi
             (cd "$TARGET_DIR" && docker compose restart "$SERVICE")
        else
            (cd "${AEGIS_DIR}" && docker compose restart)
            (cd "${BEND_DIR}" && ./scripts/manage.sh restart $LITE_ARGS $GPU_ARGS)
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
            (cd "${BEND_DIR}" && ./scripts/manage.sh down -v) # BEND's down command is smart enough
            print_success "All stacks and data have been pruned."
        else
            print_info "Prune operation cancelled."
        fi
        ;;

    *)
        usage
        ;;
esac