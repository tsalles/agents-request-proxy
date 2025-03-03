#!/bin/sh

if [ "$TLS_TERMINATION" = "true" ]; then
    echo "TLS termination is enabled."

    CERTS_DIR="certs"
    KEY_FILE="$CERTS_DIR/key.pem"
    CSR_FILE="$CERTS_DIR/csr.pem"
    CERT_FILE="$CERTS_DIR/cert.pem"

    SUBJ="/C=BR/ST=Brazil/L=Brazil/O=The Organization/CN=textgen.api"

    mkdir -p "$CERTS_DIR"

    if [ ! -f "$KEY_FILE" ] || [ ! -f "$CERT_FILE" ]; then
        echo "SSL key or certificate not found. Generating self-signed certificates..."
        openssl genpkey -algorithm RSA -out "$KEY_FILE"
        openssl req -new -key "$KEY_FILE" -out "$CSR_FILE" -subj "$SUBJ"
        openssl x509 -req -in "$CSR_FILE" -signkey "$KEY_FILE" -out "$CERT_FILE"
        echo "Self-signed certificates generated in $CERTS_DIR."
    else
        echo "SSL key and certificate found in $CERTS_DIR."
    fi

    exec uvicorn main:app --host 0.0.0.0 --port 8080 --reload --ssl-keyfile="$KEY_FILE" --ssl-certfile="$CERT_FILE"
else
    echo "TLS termination is disabled. Running in HTTP mode."
    exec uvicorn main:app --host 0.0.0.0 --port 8080 --reload
fi
