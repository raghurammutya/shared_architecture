#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

PACKAGE_NAME="shared-architecture"
GIT_BRANCH="main"
VERSION="0.4.0"

echo "🚀 Starting publishing process for $PACKAGE_NAME v$VERSION..."

# Step 1: Clean old builds
echo "🧹 Cleaning old build directories..."
rm -rf build/ dist/ *.egg-info

# Step 2: Build the package
echo "🏗 Building the package..."
python setup.py sdist bdist_wheel

# Step 3: Upload to PyPI
echo "🚀 Uploading to PyPI..."
twine upload dist/*

# Step 4: Git operations
echo "🛠 Preparing git commit and push..."
git add .
git commit -m "Release $PACKAGE_NAME version $VERSION - major enhancements"
git push origin $GIT_BRANCH

echo "✅ Publish and push complete!"
