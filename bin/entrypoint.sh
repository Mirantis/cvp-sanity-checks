#!/bin/bash

set -xe

function _info(){
  set +x
  echo -e "=== INFO: pip freeze:"
  pip freeze | sort
  echo -e "============================"
  set -x
}

_info
exec "$@"
