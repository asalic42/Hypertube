#!/bin/bash

# Generate the private Certificate Authority (CA).
# The CA is used to sign all internal TLS certificates
# (proxy, databases, etc.).

if [ -z "$1" ]; then
    echo "tls_certificate_authority.sh: certificate authority path required"
    exit 1
fi

if [ -z "$2" ]; then
    echo "tls_certificate_authority.sh: global cert dir required"
    exit 1
fi

CERT_DIR="$2"
AUTH_DIR="${CERT_DIR}/$1"

# Create the directory that will contain the CA files.
mkdir -p "${AUTH_DIR}"

# Generate the CA private key.
# This key MUST remain private because it signs every other certificate.
openssl genrsa 4096 > "${AUTH_DIR}/ca.key"

# Generate a self-signed CA certificate.
# This certificate is distributed to clients so they can trust
# certificates issued by this CA.
openssl req \
    -new -x509 \
    -nodes \
    -days 365000 \
    -key "${AUTH_DIR}/ca.key" \
    -out "${AUTH_DIR}/ca.crt" \
    -subj "/C=FR/ST=IDF/L=PARIS/O=42/OU=42/CN=CA/UID=hypertube-admin"

# Copy the CA certificate to every Django service.
# Each service uses this certificate to verify the TLS certificate
# presented by its PostgreSQL database.

DJANGO_SERVICES=(
    "users"
    "auth"
)

for SERVICE in "${DJANGO_SERVICES[@]}"; do
    CRT_DIR="services/${SERVICE}/certs"

    mkdir -p "${CRT_DIR}"
    cp "${AUTH_DIR}/ca.crt" "${CRT_DIR}/"
done