################################
# This Dockerfile is supposed to always be in synergy
# with the snapcraft.yaml of dotrun, creating the same
# environment as the snap but as a Docker container
################################

FROM ubuntu:focal

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV SNAP_VERSION="1.4.6 - Dotrun on Docker (No snapd)"

WORKDIR /tmp

# Install essential system packages
RUN apt-get update && \
    apt-get install --yes \
    git curl wget build-essential python3-dev python3-pip \
    # Install everything on snapcraft.yaml stage-packages
    gettext python3-dev libjpeg-dev libjpeg-progs libmagic1 \
    libmagickwand-dev libpng-dev libpq-dev libsodium-dev gpg \
    optipng zlib1g-dev libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libdrm2 \
    libgbm1 libnss3 libpango-1.0-0 libx11-6 libxau6 libxcb1 \
    libxcomposite1 libxdamage1 libxdmcp6 libxext6 libxfixes3 \
    libxkbcommon-x11-0 libxrandr2

# Get NodeJS
RUN arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) && \
    wget "https://deb.nodesource.com/node_16.x/pool/main/n/nodejs/nodejs_16.8.0-deb-1nodesource1_${arch}.deb"

# Get yarn
RUN wget https://github.com/yarnpkg/yarn/releases/download/v1.22.0/yarn_1.22.0_all.deb

# Install node and yarn
RUN apt-get install ./*.deb

# Copy and install dotrun
ADD src dotrun
RUN pip3 install ./dotrun
RUN rm -r /tmp/*

# Create ubuntu user
RUN groupadd --gid 1000 ubuntu
RUN useradd -rm -d /home/ubuntu -s /bin/bash -g ubuntu -G sudo -u 1000 ubuntu
USER ubuntu
WORKDIR /home/ubuntu
