#!/bin/bash

# This file used as an interface for automatic activating of virtualenv.
# Should be placed into PATH
#   Example: with_venv.sh python --version

set -xe

function _info(){
  set +x
  echo -e "===== virtualenv info: ====="
  python --version
  pip freeze | sort
  echo -e "============================"
  set -x
}

function activate_venv(){
  set +x
  if [ -f venv/bin/activate ]; then
    echo "Activating venv in $(pwd)"
    source venv/bin/activate && echo "Activated succesfully"
  else
    echo "WARNING: No venv found in $(pwd)"
    return 1
  fi
  set -x
}

activate_venv &&
_info &&
exec "$@"
