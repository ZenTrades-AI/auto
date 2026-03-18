#!/usr/bin/env bash
# exit on error
set -o errexit

export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright

pip install -r requirements.txt
playwright install chromium
playwright install-deps
