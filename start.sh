#!/bin/bash

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
  echo "Creating venv..."
  
  # Create Python virtual environment
  python3 -m venv venv
fi

echo "Activating venv..."

# Activate Python virtual environment
source venv/bin/activate

echo "Checking dependencies..."

pip install -r "src/requirements.txt"

echo "Starting the research assistant..."

python -m src

echo "Deactivating venv..."

deactivate