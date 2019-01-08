#!/bin/bash

set -xe

function _info(){
  set +x
  echo -e "=== INFO: pip freeze:"
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
}

echo "$@"
if [ "$1" = "pytest" ] || [ "$1" = "python" ] || [ "$1" = "pip" ];  then
  activate_venv &&
  _info &&
  exec "$@"
else
  exec "$@"
fi
