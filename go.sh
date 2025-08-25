#!/bin/bash

# Check for a command-line parameter (the first one: $1)
if [ -n "$1" ]; then
  # If a parameter exists, use it as the log file name
  LOG_FILE="$1_build_$(date +'%Y-%m-%d_%H-%M-%S').log"
else
  # If no parameter is provided, use the default log file name
  LOG_FILE="build_$(date +'%Y-%m-%d_%H-%M-%S').log"
fi

# --- Interactive Prompt for Cleanup ---
read -p "Do you want to clean up existing Docker containers and volumes? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Cleaning up existing containers with docker compose down..."
  docker compose down --volumes
fi

# --- Start Logging and Build Process ---
echo "Starting the build process and logging output to: $LOG_FILE"
echo "You will see a live feed of the script's progress below."
echo "--------------------------------------------------------"

# Launch start.sh, capturing all output and errors
./start.sh 2>&1 | tee "$LOG_FILE"

# Check the exit status of start.sh
if [ $? -eq 0 ]; then
  echo "--------------------------------------------------------"
  echo "✅ The build process completed successfully."
else
  echo "--------------------------------------------------------"
  echo "❌ The build process failed. Please check the log file for details."
fi