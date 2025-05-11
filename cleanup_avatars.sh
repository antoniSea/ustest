#!/bin/bash
# Script to safely clean up the avatars directory

echo "===== CLEANING UP AVATARS DIRECTORY ====="

# Check if the avatars directory exists
if [ ! -d "avatars" ]; then
    echo "Avatars directory doesn't exist. Nothing to clean up."
    exit 0
fi

# Count files in the avatars directory
FILE_COUNT=$(find avatars -type f | wc -l)
echo "Found $FILE_COUNT files in avatars directory"

# Ask for confirmation before proceeding
echo ""
echo "Are you sure you want to remove all files from the avatars directory?"
echo "This will not affect the files in the git repository, only your local copies."
read -p "Proceed? (y/n): " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Remove the contents of the avatars directory but keep the directory itself
echo "Removing files from avatars directory..."
rm -rf avatars/*

# Verify that the files were removed
REMAINING=$(find avatars -type f | wc -l)
echo "Remaining files: $REMAINING"

echo "===== CLEANUP COMPLETE ====="

# Create a .gitkeep file to maintain the directory structure
touch avatars/.gitkeep
echo "Created avatars/.gitkeep to maintain directory structure"

# Provide instructions for git
echo ""
echo "NOTE: If you want to remove these files from git as well, you will need to:"
echo "1. git rm -r --cached avatars/*"
echo "2. git commit -m \"Remove avatar files from repository\""
echo "3. git push"
echo ""
echo "Otherwise, they will remain in the repository history." 