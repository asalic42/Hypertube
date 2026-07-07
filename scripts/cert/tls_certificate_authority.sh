#!/bin/bash

if [ -z "$1" ]
  then
    echo "tls_proxy.sh: certificate authority path required"
    exit
fi

CERT_AUTH_PATH="$1"

mkdir -p ${CERT_AUTH_PATH}

openssl genrsa 4096 > ${CERT_AUTH_PATH}/ca.key
openssl req -new -x509 -nodes -days 365000 -key ${CERT_AUTH_PATH}/ca.key -out ${CERT_AUTH_PATH}/ca.crt -subj "/C=FR/ST=IDF/L=PARIS/O=42/OU=42/CN=CA/UID=hypertube-admin"