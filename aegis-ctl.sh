#!/bin/bash
set -e

# AEGIS Meta-System Control Script
# This script manages both the AEGIS agent and its required BEND backend stack.

# --- Helper Functions & Variables ---
# Determine the absolute path of the script's directory, which is the project root.
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT" # Change to the project root to ensure all paths are relative to it.

AEGIS_COMPOSE_FILE="./docker-compose.yml"
BEND_DIR="../BEND"
BEND_MANAGE_SCRIPT="$BEND_DIR/scripts/manage.sh"
BEND_HEALTHCHECK_SCRIPT="$BEND_DIR/scripts/healthcheck.sh"


# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if the BEND management script exists
if [ ! -f "$BEND_MANAGE_SCRIPT" ]; then
    echo -e "${RED}Error: BEND management script not found at '$BEND_MANAGE_SCRIPT'.${NC}"
    echo "Please ensure the BEND repository is a sibling to the AEGIS repository."
    exit 1
fi

# Usage information
usage() {
    echo -e "${YELLOW}Usage: $0 {up|up-debug|down|logs|status|airgap-bundle} [--gpu]${NC}"
    echo
    echo "Commands:"
    echo "  up                - Start both the BEND backend and the AEGIS agent in detached mode."
    echo "  up-debug          - Start BEND, wait, then start AEGIS in the foreground, streaming all logs."
    echo "  down              - Stop both the AEGIS agent and the BEND backend."
    echo "  logs [service]    - Tail logs for a service. Prefers AEGIS, falls back to BEND."
    echo "  status            - Check the health of all AEGIS and BEND services."
    echo "  airgap-bundle     - Create a distributable package for offline deployment."
    echo
    echo "Options:"
    echo "  --gpu             - When used with 'up' or 'up-debug', builds BEND services with NVIDIA GPU support."
    exit 1
}

# --- Command Dispatch ---
COMMAND=$1
shift # Remove the command from the arguments list

case "$COMMAND" in
    up | up-debug)
        echo -e "${YELLOW}--- Checking for Shared Docker Network ---${NC}"
        # Ensure the shared network exists before starting any services.
        docker network inspect aegis_bend_net >/dev/null 2>&1 || {
            echo "Shared network 'aegis_bend_net' not found. Creating it..."
            docker network create aegis_bend_net
            echo -e "${GREEN}Network 'aegis_bend_net' created.${NC}"
        }

        echo -e "\n${YELLOW}--- Bringing up the BEND Backend ---${NC}"
        # Always start BEND in detached mode. Pass any extra args like --gpu.
        "$BEND_MANAGE_SCRIPT" up "$@"

        echo -e "\n${YELLOW}--- Waiting for BEND services to be healthy ---${NC}"
        "$BEND_HEALTHCHECK_SCRIPT"
        HEALTH_CHECK_STATUS=$?

        if [ $HEALTH_CHECK_STATUS -ne 0 ]; then
            echo -e "🔴 ${RED}BEND health check failed. AEGIS will not be started.${NC}"
            echo "   Check the BEND logs with: $0 logs koboldcpp"
            exit 1
        fi
        echo -e "${GREEN}✅ BEND services are online.${NC}"


        echo -e "\n${YELLOW}--- Bringing up the AEGIS Agent ---${NC}"
        if [ "$COMMAND" == "up-debug" ]; then
            # For debug, start AEGIS in the foreground to stream its logs.
            docker compose -f "$AEGIS_COMPOSE_FILE" up --build
        else
            # For normal up, start AEGIS detached.
            docker compose -f "$AEGIS_COMPOSE_FILE" up -d --build
            echo -e "\n${GREEN}✅ AEGIS+BEND stack is running. Use './aegis-ctl.sh status' to check health.${NC}"
        fi
        ;;

    down)
        echo -e "${YELLOW}--- Taking down the AEGIS Agent ---${NC}"
        docker compose -f "$AEGIS_COMPOSE_FILE" down

        echo -e "\n${YELLOW}--- Taking down the BEND Backend ---${NC}"
        "$BEND_MANAGE_SCRIPT" down

        echo -e "\n${GREEN}✅ AEGIS+BEND stack has been stopped.${NC}"
        ;;

    logs)
        SERVICE=$1
        if [ -z "$SERVICE" ]; then
            echo -e "${RED}Error: You must specify which service to log (e.g., 'agent', 'koboldcpp').${NC}"
            exit 1
        fi

        # Check if the service exists in the AEGIS compose file first
        if docker compose -f "$AEGIS_COMPOSE_FILE" ps --services | grep -q "^${SERVICE}$"; then
            echo -e "${YELLOW}Tailing logs for AEGIS service '$SERVICE'... (Ctrl+C to exit)${NC}"
            docker compose -f "$AEGIS_COMPOSE_FILE" logs -f "$SERVICE"
        else
            # If not, delegate to the BEND management script
            echo -e "${YELLOW}Service '$SERVICE' not in AEGIS, checking BEND...${NC}"
            "$BEND_MANAGE_SCRIPT" logs "$SERVICE"
        fi
        ;;

    status)
        echo -e "${YELLOW}--- AEGIS Service Status ---${NC}"
        # A simple check for the agent container by checking the compose project's running services
        if docker compose -f "$AEGIS_COMPOSE_FILE" ps --status=running | grep -q "agent"; then
             echo -e "[ ${GREEN}✅ ONLINE${NC} ] aegis-agent"
        else
             echo -e "[ ${RED}❌ OFFLINE${NC} ] aegis-agent"
        fi

        echo -e "\n${YELLOW}--- BEND Service Status ---${NC}"
        "$BEND_MANAGE_SCRIPT" status
        ;;

    airgap-bundle)
        echo -e "${YELLOW}--- Preparing AEGIS Airgap Bundle ---${NC}"

        # 1. Prepare BEND bundle
        echo -e "\n${YELLOW}Step 1: Preparing BEND assets...${NC}"
        "$BEND_MANAGE_SCRIPT" airgap-bundle

        # 2. Build and save AEGIS image
        echo -e "\n${YELLOW}Step 2: Building and saving AEGIS agent image...${NC}"
        docker compose -f "$AEGIS_COMPOSE_FILE" build agent
        docker save aegis-agent:latest -o aegis-agent-image.tar

        # 3. Create README
        echo -e "\n${YELLOW}Step 3: Creating deployment instructions...${NC}"
        cat > README-AIRGAP.md <<- EOM
# AEGIS Airgap Deployment Instructions

This bundle contains all necessary components to run the AEGIS+BEND stack in an offline environment.

## Prerequisites

- Docker and Docker Compose
- A system with the \`tar\` utility.
- For GPU support, NVIDIA drivers and the NVIDIA Container Toolkit must be installed on the target host.

## Deployment Steps

1.  **Transfer Bundle:** Copy the \`aegis-airgap-package.tar.gz\` file to the airgapped machine.

2.  **Extract Bundle:**
    \`\`\`bash
    tar -xzvf aegis-airgap-package.tar.gz
    cd aegis-airgap-package
    \`\`\`

3.  **Load Docker Images:**
    \`\`\`bash
    # Load BEND images
    docker load -i BEND/bend-images.tar
    # Load AEGIS image
    docker load -i aegis-agent-image.tar
    \`\`\`

4.  **Run the Stack:** Use the included control script.
    - **For CPU deployment:**
      \`\`\`bash
      ./aegis-ctl.sh up
      \`\`\`
    - **For NVIDIA GPU deployment:**
      \`\`\`bash
      ./aegis-ctl.sh up --gpu
      \`\`\`

5.  **Access the UI:** The AEGIS dashboard will be available at \`http://<host_ip>:8000\`.

EOM

        # 4. Create the final package
        echo -e "\n${YELLOW}Step 4: Creating final package: aegis-airgap-package.tar.gz...${NC}"
        tar -czf aegis-airgap-package.tar.gz \
            --exclude='*.git' \
            --exclude='*.pyc' \
            --exclude='__pycache__' \
            .

        # Cleanup intermediate files
        rm aegis-agent-image.tar README-AIRGAP.md
        rm BEND/bend-images.tar

        echo -e "\n${GREEN}✅ Success! Airgap bundle created: aegis-airgap-package.tar.gz${NC}"
        ;;

    *)
        usage
        ;;
esac
