#!/bin/bash
set -a
source .env
set +a
echo ${CERTIFICATE_AUTHORITY_PATH}
./scripts/cert/set_up.sh


