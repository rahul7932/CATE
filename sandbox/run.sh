#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || { python -m venv .venv && source .venv/bin/activate; }
pip install -q flask requests
python sandbox/run.py
