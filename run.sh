#!/bin/bash
# This script sets up the environment for the project and starts the application
cd "$(dirname "$0")"
python3 main.py
read -p "Press enter to exit"
