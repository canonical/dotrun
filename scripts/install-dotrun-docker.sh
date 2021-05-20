#! /usr/bin/env bash

set -e

echo "Installing dotrun..."

# Add user to docker group
sudo addgroup --system docker
sudo adduser $USER docker
newgrp docker

# Install docker and dotrun snaps
sudo snap install docker
sudo snap install dotrun

# Do needed snap connects
sudo snap connect dotrun:dot-npmrc
sudo snap connect dotrun:dot-yarnrc
sudo snap connect dotrun:docker-executables docker:docker-executables
sudo snap connect dotrun:docker-cli docker:docker-daemon

echo "Dotrun and docker snaps are installed and connected"
