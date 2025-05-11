#!/bin/bash
# Script to push all presentation JSON files to the repository

echo "===== PUSHING ALL PRESENTATION JSON FILES ====="

# Make sure the presentations directory exists
if [ ! -d "presentations" ]; then
    echo "ERROR: presentations directory not found!"
    exit 1
fi

# Count JSON files
JSON_COUNT=$(find presentations -name "*.json" | wc -l)
echo "Found $JSON_COUNT JSON files in presentations folder"

if [ $JSON_COUNT -eq 0 ]; then
    echo "No JSON files found to push."
    exit 0
fi

# Create the presentations directory in git if it doesn't exist
mkdir -p presentations

# Add all JSON files to git
echo "Adding all presentation JSON files to git..."
git add presentations/*.json

# Add the modified .gitignore
git add .gitignore

# Create avatars directory if it doesn't exist
if [ ! -d "avatars" ]; then
    mkdir -p avatars
    echo "Created avatars directory"
fi

# Add the directories to git
git add -f presentations avatars

# Commit the changes
echo "Committing presentation files..."
git commit -m "Add all presentation JSON files"

# Push to the repository
echo "Pushing to repository..."
git push

echo "===== COMPLETED PUSHING PRESENTATION FILES ====="
echo "JSON files pushed: $JSON_COUNT" 