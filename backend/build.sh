#!/usr/bin/env bash
# Render build script — installs dependencies, initializes the database,
# and seeds demo data for hackathon presentations.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create tables (idempotent — safe to run on every deploy)
python init_db.py

# Add columns that create_all cannot add to an existing table. Idempotent
# and dialect-agnostic, so it is safe on every deploy including the first.
python migrate_add_system_admin.py
python migrate_add_void_columns.py

# Report any drift between the live schema and the models. Read-only, and
# deliberately non-fatal (|| true): create_all above cannot add columns to
# an existing table, and this is the only place that gap becomes visible
# on a plan without shell access -- read it in the deploy log. A failing
# check must not block a deploy that is otherwise fine.
python check_schema.py || true

# Seed demo data (idempotent — skips records that already exist).
# Provides admin, 5 students, and 2 exams with questions for demo.
python -m app.cli.seed_demo_data
