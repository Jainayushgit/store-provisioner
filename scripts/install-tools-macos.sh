#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required"
  exit 1
fi

brew install docker kubectl helm k3d colima

if ! colima status >/dev/null 2>&1; then
  colima start --cpu 4 --memory 6 --disk 40
fi

echo "Installed docker, kubectl, helm, k3d, colima"
echo "Colima started (if it was not already running)"
