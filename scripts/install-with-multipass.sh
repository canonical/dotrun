#!/bin/bash

# Bash strict mode
set -euo pipefail

# Get machine type
case "$(uname -s)" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    *)          machine="NO_SUPPORT"
esac

if [ "$machine" = "NO_SUPPORT" ]; then
    echo "Your system is not supported, contact a developer."
    exit 1
fi

title () {
   echo -e "\n$1\n--------\n"
}

########################
# Installing multipass #
########################

title "Installing multipass"

if ! command -v multipass &> /dev/null
then
    if [ "$machine" = "Linux" ]; then
        snap install multipass
    else
        curl -L https://multipass.run/download/macos --output multipass.pkg
        sudo installer -pkg multipass.pkg -target /
        sleep 5
    fi
else
    echo "Multipass is installed"
fi


##########################
# Multipass dotrun image #
##########################

title "Configuring multipass"

if multipass info dotrun &> /dev/null; then
    echo "There is already a dotrun instance."
    echo "If you want to remove it: multipass delete -p dotrun"
else
    if [ "$machine" = "Linux" ]; then
        TOTAL_CPUS=$(nproc)
        TOTAL_MEM=$(awk '/^Mem/ {print $2}' <(free -h --mega))
    else
        TOTAL_CPUS=$(sysctl -n hw.ncpu)
        TOTAL_MEM=$(sysctl -n hw.memsize)
    fi

    curl -s https://raw.githubusercontent.com/canonical-web-and-design/dotrun/master/scripts/cloud-init-dotrun.yaml | multipass launch --cpus $TOTAL_CPUS --mem $TOTAL_MEM --disk 50G --name dotrun --cloud-init -
fi

##########################
# Mount shared directory #
##########################

title "Mount shared directory"

if mount | grep "on $HOME/dotrun-projects" > /dev/null; then
    echo "Folder is already mounted"
else
    mkdir -p $HOME/dotrun-projects
    DOTRUN_IP=$(multipass info dotrun | grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b")

    if [ "$machine" = "Linux" ]; then
        sudo mount -t nfs $DOTRUN_IP:/home/ubuntu/dotrun-projects $HOME/dotrun-projects
    else
        mount -o nolocks -t nfs $DOTRUN_IP:/home/ubuntu/dotrun-projects $HOME/dotrun-projects
    fi

    echo "Folder mounted"
fi


####################
# Set dotrun alias #
####################

title "Install dotrun bash function"

if [ "$machine" = "Linux" ]; then
    # The cd workaround is because the multipass snap doesn't work on a NFS mounted folder
    FUNCTION='dotrun() {
    SITE=$(realpath --relative-base="$HOME" .)
    cd
    multipass exec dotrun -- dotrun -C $SITE "$@" ; cd $SITE
}'
else
    FUNCTION='dotrun() {
    SITE="${$(pwd)#$HOME/}"
    multipass exec dotrun -- dotrun -C $SITE "$@"
}'
fi

# Bash users
if grep -q "dotrun()" $HOME/.bashrc; then
    echo ".bashrc: Removing previous dotrun()"
    sed -i'' -e '/^dotrun()/,/^}/d' $HOME/.bashrc
fi

echo "Adding dotrun function to .bashrc"
echo -e "\n$FUNCTION" >> $HOME/.bashrc


# zsh users
if [ -f $HOME/.zshrc ]; then
    if grep -q "dotrun()" $HOME/.zshrc; then
        echo ".zshrc: Removing previous dotrun()"
        sed -i'' -e '/^dotrun()/,/^}/d' $HOME/.zshrc
    fi

    echo "Adding dotrun function to .zshrc"
    echo -e "\n$FUNCTION" >> $HOME/.zshrc
fi

echo -e "Finish!\nPlease restart your terminal"
