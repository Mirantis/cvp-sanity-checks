#!/bin/bash
set -x
echo "Start pre-build"
# export GIT_SSH_COMMAND="${GIT_SSH_COMMAND} -A"
export GIT_SSH_COMMAND="ssh -A"
echo $SSH_AUTH_SOCK
git submodule init
git submodule update --remote