#!/usr/bin/env bash
# ==============================================================================
# Script: sync_git.sh
# Purpose: Automatically stages, commits, and pushes repository changes to GitHub
# Usage: ./sync_git.sh "Added hardware watchdog timer"
# ==============================================================================

# Exit immediately if a command exits with a non-zero (error) status
set -e

# Capture the first command-line argument passed to the script
COMMIT_MSG="$1"

# If no argument was provided on the command line, prompt for one
if [ -z "$COMMIT_MSG" ]; then
    echo -n "Enter commit description: "
    read -r COMMIT_MSG
fi

# Fallback: if input is still empty, apply an automated timestamped message
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Routine project update: $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "[*] Checking repository status and staging files..."
git add .

# Check if there are changes between staged files and the last commit (HEAD)
if git diff-index --quiet HEAD --; then
    echo "[-] No changes detected. Working tree is clean."
    exit 0
fi

echo "[*] Committing changes with message: '$COMMIT_MSG'..."
git commit -m "$COMMIT_MSG"

echo "[*] Pushing commits to GitHub..."
git push origin main

echo "[+] Successfully synchronized with GitHub!"

