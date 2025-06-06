#!/bin/bash
# This script sets up the environment for the project and starts the application with all passed arguments
cd "$(dirname "$0")"
python3 main.py "$@"
