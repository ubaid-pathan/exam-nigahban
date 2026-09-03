#!/usr/bin/env bash
# Render build script — installs dependencies and initializes the database.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create tables (idempotent — safe to run on every deploy)
python init_db.py
