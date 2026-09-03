#!/usr/bin/env bash
# Render build script — installs dependencies, initializes the database,
# and seeds demo data for hackathon presentations.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create tables (idempotent — safe to run on every deploy)
python init_db.py

# Seed demo data (idempotent — skips records that already exist).
# Provides admin, 5 students, and 2 exams with questions for demo.
python -m app.cli.seed_demo_data
