#!/bin/bash
# Build script for FastSM using Nuitka

echo "========================================"
echo "Building FastSM with Nuitka"
echo "========================================"
echo

# Check if Nuitka is installed
if ! python3.11 -m nuitka --version > /dev/null 2>&1; then
    echo "Nuitka is not installed. Installing..."
    pip3.11 install nuitka
    if [ $? -ne 0 ]; then
        echo "Failed to install Nuitka"
        exit 1
    fi
fi

# Run the build script
python3.11 build.py

echo
echo "Build complete. Press Enter to exit..."
read
