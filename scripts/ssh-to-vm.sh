#!/bin/bash

# Script to SSH into fansboda-dev-vm-instance on Google Cloud Platform
# Usage: ./scripts/ssh-to-vm.sh [command]
# If no command is provided, opens an interactive SSH session

set -e

# Configuration
VM_NAME="fansboda-dev-vm-instance"
ZONE="us-central1-a"
PROJECT="fansboda-project"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Connecting to ${VM_NAME}...${NC}"

# Check if a command was provided
if [ $# -eq 0 ]; then
    # No command provided - open interactive SSH session
    echo -e "${GREEN}Opening interactive SSH session...${NC}"
    echo -e "${BLUE}Use 'exit' to disconnect${NC}"
    gcloud compute ssh "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT" \
        --tunnel-through-iap
else
    # Command provided - execute it remotely
    echo -e "${GREEN}Executing command on remote VM...${NC}"
    gcloud compute ssh "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT" \
        --tunnel-through-iap \
        --quiet \
        --command="$*"
fi

