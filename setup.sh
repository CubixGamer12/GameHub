#!/bin/bash

# GameHub Setup Script
# This script ensures all system dependencies are installed before running the Python installer.

set -e

echo "Checking system dependencies..."

# Check for updates
if [ -d ".git" ]; then
    echo "Checking for updates..."
    git fetch
    
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    
    if [ $LOCAL != $REMOTE ]; then
        echo "New version available!"
        read -p "Do you want to update? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Updating..."
            git pull
            echo "Update complete. Restarting setup..."
            exec "$0" "$@"
        fi
    else
        echo "GameHub is up to date."
    fi
fi

# Detect Package Manager
PM=""
if command -v pacman &> /dev/null; then
    PM="pacman"
elif command -v apt &> /dev/null; then
    PM="apt"
elif command -v dnf &> /dev/null; then
    PM="dnf"
else
    echo "Error: specific package manager not found (pacman, apt, dnf)."
    echo "Please install dependencies manually."
    exit 1
fi

echo "Detected package manager: $PM"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not found."
    exit 1
fi

# Check for pip (usually included with python, but good to check)
if ! python3 -m pip --version &> /dev/null; then
    echo "pip is required but not found."
    exit 1
fi

# Check for critical GUI libraries
# We invoke python to check for imports
MISSING_DEPS=0
python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk, Adw" 2>/dev/null || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    echo "Missing critical dependencies (Gtk4, Libadwaita, PyGObject)."
    echo "Attempting to install..."
    
    if [ "$PM" = "pacman" ]; then
        sudo pacman -S --needed --noconfirm python-gobject gtk4 libadwaita python-pip
    elif [ "$PM" = "apt" ]; then
        sudo apt update
        sudo apt install -y python3-gi libgtk-4-dev libadwaita-1-dev python3-pip
    elif [ "$PM" = "dnf" ]; then
        sudo dnf install -y python3-gobject gtk4 libadwaita python3-pip
    fi
else
    echo "System dependencies are satisfied."
fi

# Launch the Python Installer
echo "Launching Installer..."
exec python3 install.py
