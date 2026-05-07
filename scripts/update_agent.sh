#!/bin/bash
set -e

PROJECT_DIR="/opt/monitoring-project"
TARGET_DIR="/opt/monitoring-agent"

echo "Monitoring agent update gestart"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Project directory bestaat niet: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

echo "Nieuwe versie ophalen via git"
git pull

echo "Doelmap aanmaken als deze nog niet bestaat"
mkdir -p "$TARGET_DIR"

echo "Agentbestanden kopiëren naar $TARGET_DIR"
rsync -av --delete \
  --exclude "agent_config.py" \
  agents/linux/ "$TARGET_DIR/"

echo "Python dependencies installeren"
pip3 install -r "$PROJECT_DIR/requirements.txt"

echo "Monitoring agent herstarten"
systemctl restart monitoring-agent

echo "Status monitoring-agent:"
systemctl status monitoring-agent --no-pager

echo "Monitoring agent update voltooid"