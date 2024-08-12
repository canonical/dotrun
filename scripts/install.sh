#!/bin/bash

set -e

install_pipx_macos() {
    if command -v brew >/dev/null 2>&1; then
        echo "Installing pipx using Homebrew..."
        brew install pipx
    else
        echo "Error: Homebrew is not installed on your system."
        echo "Please install Homebrew first: https://brew.sh/"
        echo "Then run this script again."
        exit 1
    fi
}
notice_shown=false

sudo_notice() {
    if $notice_shown; then
        return
    fi
    echo "-------------------------------------"
    echo "This step requires sudo privileges to install system packages."
    echo "You may be prompted to enter your password."
    echo "-------------------------------------"
    notice_shown=true
}
try_sudo() {
    # if sudo not installed
    if ! command -v sudo >/dev/null 2>&1; then
        "$@"
    elif [ -z "${SUDO_USER-}" ]; then
        sudo_notice
        sudo "$@"
    else
        "$@"
    fi
}

install_pipx_linux() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing pipx using apt..."
        sudo_notice
        try_sudo apt update
        try_sudo apt install -y pipx
    elif command -v dnf >/dev/null 2>&1; then
        echo "Installing pipx using dnf..."
        sudo_notice
        try_sudo dnf install -y pipx
    elif command -v pacman >/dev/null 2>&1; then
        echo "Installing pipx using pacman..."
        sudo_notice
        try_sudo pacman -Sy --noconfirm python-pipx
    else
        echo "Error: Your linux distribution is not supported by this script."
        echo "Please follow the manual installation instructions: https://github.com/canonical/dotrun?tab=readme-ov-file#installation"
        exit 1
    fi
}

# Detect the operating system
# macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    install_pipx_macos
# Linux
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    install_pipx_linux
else
    echo "Unsupported operating system: $OSTYPE"
    echo "Please follow the manual installation instructions: https://github.com/canonical/dotrun?tab=readme-ov-file#installation"
    exit 1
fi

# Install dotrun using pipx
echo "Installing dotrun..."
pipx install dotrun

echo "Installation complete!"
pipx ensurepath
