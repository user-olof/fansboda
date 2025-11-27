#!/bin/bash

# Script to delete all SSH keys from OS Login profile
# This helps resolve the "Login profile size exceeds 32 KiB" error

# Don't use set -e here as we want to handle errors gracefully

echo "=== Fetching list of SSH keys from OS Login ==="
SSH_KEYS=$(gcloud compute os-login ssh-keys list --format="value(FINGERPRINT)" 2>/dev/null || echo "")

if [ -z "$SSH_KEYS" ]; then
    echo "No SSH keys found in OS Login profile."
    exit 0
fi

KEY_COUNT=$(echo "$SSH_KEYS" | wc -l | tr -d ' ')
echo "Found $KEY_COUNT SSH key(s) to remove."
echo ""

# Remove each SSH key
REMOVED=0
FAILED=0

while IFS= read -r fingerprint; do
    if [ -z "$fingerprint" ]; then
        continue
    fi
    
    echo "Removing SSH key: $fingerprint"
    
    # Try with --key flag first, then fallback to positional argument
    if gcloud compute os-login ssh-keys remove --key="$fingerprint" 2>/dev/null || \
       gcloud compute os-login ssh-keys remove "$fingerprint" 2>/dev/null; then
        echo "  ✓ Successfully removed: $fingerprint"
        ((REMOVED++))
    else
        echo "  ✗ Failed to remove: $fingerprint"
        ((FAILED++))
    fi
    echo ""
done <<< "$SSH_KEYS"

echo "=== Summary ==="
echo "Successfully removed: $REMOVED key(s)"
echo "Failed to remove: $FAILED key(s)"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Warning: Some keys could not be removed. You may need to:"
    echo "1. Check your permissions"
    echo "2. Try using the REST API directly"
    echo "3. Disable OS Login and use traditional SSH keys"
    exit 1
fi

echo ""
echo "All SSH keys have been removed successfully!"

