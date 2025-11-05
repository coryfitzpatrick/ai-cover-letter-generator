#!/bin/bash
# Setup script to move data to Google Drive

set -e  # Exit on error

echo "========================================="
echo "Google Drive Data Setup"
echo "========================================="
echo ""

# Define paths
GOOGLE_DRIVE_BASE="$HOME/Library/CloudStorage"
EMAIL="coryartfitz@gmail.com"
FOLDER_NAME="AI Data"

# Find Google Drive folder
echo "Looking for Google Drive installation..."
GOOGLE_DRIVE_FOLDER=$(find "$GOOGLE_DRIVE_BASE" -maxdepth 1 -type d -name "GoogleDrive-$EMAIL" 2>/dev/null | head -1)

if [ -z "$GOOGLE_DRIVE_FOLDER" ]; then
    echo ""
    echo "⚠️  Google Drive not found at: $GOOGLE_DRIVE_BASE"
    echo ""
    echo "Please install Google Drive for Desktop:"
    echo "  https://www.google.com/drive/download/"
    echo ""
    echo "After installing, run this script again."
    exit 1
fi

echo "✓ Found Google Drive at: $GOOGLE_DRIVE_FOLDER"
echo ""

# Set up paths
MY_DRIVE="$GOOGLE_DRIVE_FOLDER/My Drive"
DATA_FOLDER="$MY_DRIVE/$FOLDER_NAME"

# Create folder in Google Drive
echo "Creating '$FOLDER_NAME' folder in Google Drive..."
mkdir -p "$DATA_FOLDER"
echo "✓ Folder created at: $DATA_FOLDER"
echo ""

# Copy files
echo "Copying PDF files to Google Drive..."
if ls data/*.pdf 1> /dev/null 2>&1; then
    cp -v data/*.pdf "$DATA_FOLDER/"
    echo "✓ PDF files copied"
else
    echo "⚠️  No PDF files found in data/ directory"
fi
echo ""

# Copy LinkedIn data
echo "Copying LinkedIn export data..."
if ls -d data/linkedin-export-* 1> /dev/null 2>&1; then
    cp -rv data/linkedin-export-* "$DATA_FOLDER/"
    echo "✓ LinkedIn data copied"
else
    echo "⚠️  No LinkedIn export found"
fi
echo ""

# Update .env file
echo "Updating .env file..."
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example "$ENV_FILE"
fi

# Check if DATA_DIR already exists in .env
if grep -q "^DATA_DIR=" "$ENV_FILE"; then
    echo "⚠️  DATA_DIR already set in .env"
    echo "Current value:"
    grep "^DATA_DIR=" "$ENV_FILE"
    echo ""
    read -p "Do you want to update it? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old DATA_DIR line
        sed -i.backup '/^DATA_DIR=/d' "$ENV_FILE"
        echo "DATA_DIR=$DATA_FOLDER" >> "$ENV_FILE"
        echo "✓ DATA_DIR updated in .env"
    else
        echo "Skipping .env update"
    fi
else
    # Add DATA_DIR to .env
    echo "" >> "$ENV_FILE"
    echo "# Data directory pointing to Google Drive" >> "$ENV_FILE"
    echo "DATA_DIR=$DATA_FOLDER" >> "$ENV_FILE"
    echo "✓ DATA_DIR added to .env"
fi
echo ""

# Rebuild database
echo "========================================="
echo "Next Steps"
echo "========================================="
echo ""
echo "1. Activate your virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Rebuild the ChromaDB database:"
echo "   prepare-data"
echo ""
echo "3. Test the setup:"
echo "   cover-letter-cli"
echo ""
echo "Your data is now in: $DATA_FOLDER"
echo ""
echo "Note: The local data/ folder is now ignored by git."
echo "You can safely delete the local PDF files after verifying everything works:"
echo "   rm data/*.pdf"
echo "   rm -rf data/linkedin-export-*"
echo ""
