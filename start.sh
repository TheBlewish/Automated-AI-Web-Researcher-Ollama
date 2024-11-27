#!/bin/bash

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

pip install -r "src/requirements.txt"

python -m src

deactivate