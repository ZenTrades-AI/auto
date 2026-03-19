#!/usr/bin/env bash
# exit on error
set -o errexit

# CRITICAL: Force playwright to install INSIDE the project directory so Render doesn't delete it after the build phase!
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/src/.playwright"

pip install -r requirements.txt
playwright install chromium
playwright install-deps
