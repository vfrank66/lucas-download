#!/bin/bash
# Upload Brazilian Chamber PDF archives to GitHub
# This script helps manage the upload process for large files

echo "========================================="
echo "Brazilian Chamber PDF Archive Uploader"
echo "========================================="
echo

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository!"
    exit 1
fi

# Check if Git LFS is installed
if ! command -v git-lfs &> /dev/null; then
    echo "Error: Git LFS is not installed!"
    echo "Please install Git LFS first:"
    echo "  macOS: brew install git-lfs"
    echo "  Ubuntu: sudo apt install git-lfs"
    exit 1
fi

# Initialize Git LFS if not already done
echo "Initializing Git LFS..."
git lfs install

# Add all archive files
echo "Adding archive files to git..."
git add archives/
git add *.py
git add *.md
git add .gitattributes
git add .gitignore

# Check repository size
echo "Checking repository size..."
git count-objects -vH

# Show LFS files
echo "Git LFS tracked files:"
git lfs ls-files

# Commit changes
echo "Committing changes..."
read -p "Enter commit message (or press Enter for default): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Add compressed PDF archives for Brazilian Chamber documents"
fi

git commit -m "$commit_msg"

# Push to GitHub
echo "Pushing to GitHub..."
echo "Note: This may take a while for large files..."
git push origin main

echo "Upload completed!"
echo "Check your GitHub repository for the uploaded archives."
