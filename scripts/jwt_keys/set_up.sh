KEY_DIR=jwt_keys
PUBLIC_KEY=jwt_public.pem
PRIVATE_KEY=jwt_private.pem

mkdir -p "${KEY_DIR}"

openssl genpkey -algorithm RSA -out "${KEY_DIR}/${PRIVATE_KEY}" -pkeyopt rsa_keygen_bits:4096
openssk rsa -pubout -in "${KEY_DIR}/${PRIVATE_KEY}" -out "${KEY_DIR}/${PUBLIC_KEY}"

AUTH_SERVICE=auth

AUTH_JWT_DIR="services/${AUTH_SERVICE}/jwt"
mkdir -p "${AUTH_JWT_DIR}"
cp "${PUBLIC_KEY}" "${AUTH_JWT_DIR}"
cp "${PRIVATE_KEY}" "${AUTH_JWT_DIR}"

OTHER_SERVICES=(
    "users"
    "movies"
)

for SERVICE in "${OTHER_SERVICES[@]}"; do
    SERV_JWT_DIR="services/${SERVICE}/jwt"

    mkdir -p "${SERV_JWT_DIR}"
    cp "${KEY_DIR}/${PUBLIC_KEY}" "${SERV_JWT_DIR}/"
done