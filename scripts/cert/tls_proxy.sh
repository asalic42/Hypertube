#!/bin/bash

if [ -z "$1" ]
  then
    echo "tls_proxy.sh: certificate authority path required"
    exit
fi

CERT_AUTH_PATH="$1"
SERVICE_NAME=proxy
SERVICE_CERTS=./services/proxy/certs

mkdir -p $SERVICE_CERTS

$GEN_CSR ${SERVICE_CERTS}/${SERVICE_NAME}.csr -keyout ${SERVICE_CERTS}/${SERVICE_NAME}.key -subj "/C=FR/ST=IDF/L=PARIS/O=42/OU=42/CN=${SERVICE_NAME}/UID=hypertube-admin" 
$GEN_CRT ${SERVICE_CERTS}/${SERVICE_NAME}.csr -out ${SERVICE_CERTS}/${SERVICE_NAME}.crt -CA ${CERT_AUTH_PATH}/ca.crt -CAkey ${CERT_AUTH_PATH}/ca.key

cp ${CERT_AUTH_PATH}/ca.crt ${SERVICE_CERTS}/ca.crt