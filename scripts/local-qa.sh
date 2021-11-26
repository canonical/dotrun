#! /usr/bin/env bash

rm dotrun_*.snap
sudo snap remove --purge dotrun

set -e

snapcraft clean
snapcraft
snap install --dangerous dotrun_*.snap
sudo snap connect dotrun:dot-npmrc
sudo snap connect dotrun:dot-yarnrc
sudo snap connect dotrun:docker-executables docker:docker-executables
sudo snap connect dotrun:docker-cli docker:docker-daemon
