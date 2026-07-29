#!/bin/bash

# Generate all TLS assets required by the project.
#
# Generation order:
#   1. Create the private Certificate Authority (CA).
#   2. Generate the reverse proxy certificate signed by the CA.
#   3. Generate the database certificate signed by the CA.
#
# The generated certificates are copied into each service directory
# so they can be mounted into their respective containers.


# OpenSSL helper commands shared by all certificate generation scripts.
export GEN_CSR="openssl req -new -newkey rsa:4096 -nodes -out"
export GEN_CRT="openssl x509 -req -days 365000 -in"

SCRIPT_DIR=./scripts/cert

# Global directory containing all generated certificates.
CERT_DIR=certs

# Directory containing the Certificate Authority files.
CERT_AUTHORITY_DIR=ca

mkdir -p "${CERT_DIR}"

# Generate the project's private Certificate Authority.
"${SCRIPT_DIR}/tls_certificate_authority.sh" "${CERT_AUTHORITY_DIR}" "${CERT_DIR}"

# Generate the HTTPS certificate for the Nginx reverse proxy.
"${SCRIPT_DIR}/tls_proxy.sh" "${CERT_AUTHORITY_DIR}" "${CERT_DIR}"

# Generate the PostgreSQL server certificate.
"${SCRIPT_DIR}/tls_db.sh" "${CERT_AUTHORITY_DIR}" "${CERT_DIR}"