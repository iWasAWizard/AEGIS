#!/bin/bash
# aegis/scripts/sync_models.sh
# A utility to synchronize the AEGIS models.yaml with the canonical manifest from BEND.

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Main Logic ---
cd "$(dirname "$0")/.." || exit # Ensure we are in the AEGIS root directory

if ! command -v yq &> /dev/null; then
    echo -e "${RED}ERROR: yq is not installed. Please install it to use this script (e.g., 'brew install yq').${NC}"
    exit 1
fi

BEND_MANIFEST="../BEND/models.yaml"
AEGIS_MANIFEST="./models.yaml"

if [ ! -f "$BEND_MANIFEST" ]; then
    echo -e "${RED}ERROR: BEND manifest not found at '$BEND_MANIFEST'.${NC}"
    echo "Please ensure the AEGIS and BEND repositories are in the same parent directory."
    exit 1
fi

echo -e "${BLUE}Syncing model definitions from BEND to AEGIS...${NC}"

# Use yq to extract only the fields AEGIS needs and create a new YAML structure.
# This ensures AEGIS has a clean, relevant manifest without backend-specific details.
yq e '{ "models": .models | map({ "key": .key, "name": .name, "formatter_hint": .formatter_hint, "notes": .notes }) }' "$BEND_MANIFEST" > "$AEGIS_MANIFEST"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: AEGIS models.yaml has been synchronized with the BEND manifest.${NC}"
else
    echo -e "${RED}ERROR: Failed to synchronize models. Please check your yq installation and file permissions.${NC}"
    exit 1
fi