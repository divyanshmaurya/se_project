#!/bin/bash
set -euo pipefail
source /var/app/venv/*/bin/activate
cd /var/app/staging
python3 manage.py collectstatic --noinput
