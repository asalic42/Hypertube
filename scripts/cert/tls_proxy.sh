#!/bin/bash

# Generate the TLS certificate used by the Nginx reverse proxy.
# This certificate is presented to browsers during the HTTPS handshake.

if [ -z "$1" ]; then
    echo "tls_proxy.sh: certificate authority path required"
    exit 1
fi

if [ -z "$2" ]; then
    echo "tls_proxy.sh: global cert dir required"
    exit 1
fi

CERT_DIR="$2"
AUTH_DIR="${CERT_DIR}/$1"

SERVICE_NAME=proxy
SERVICE_CERTS_DIR="${CERT_DIR}/${SERVICE_NAME}"

mkdir -p "${SERVICE_CERTS_DIR}"

# Generate:
#   - a private key
#   - a Certificate Signing Request (CSR)
#
# The CSR contains the database public key and identity.
$GEN_CSR \
    "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.csr" \
    -keyout "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.key" \
    -subj "/C=FR/ST=IDF/L=PARIS/O=42/OU=42/CN=${SERVICE_NAME}/UID=hypertube-admin" \
    -addext "subjectAltName=DNS:${SERVICE_NAME}"

# Sign the CSR using the private CA.
# The resulting certificate is trusted by any client that trusts ca.crt.
$GEN_CRT \
    "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.csr" \
    -out "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.crt" \
    -CA "${AUTH_DIR}/ca.crt" \
    -CAkey "${AUTH_DIR}/ca.key"

# Copy the database certificate and private key into the PostgreSQL
# service directory so they can be mounted inside the container.
mkdir -p "services/${SERVICE_NAME}/certs"

cp "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.key" "services/${SERVICE_NAME}/certs"
cp "${SERVICE_CERTS_DIR}/${SERVICE_NAME}.crt" "services/${SERVICE_NAME}/certs"