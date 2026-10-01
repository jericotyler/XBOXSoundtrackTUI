#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install textual 
else
    source venv/bin/activate
fi
python3 app.py
