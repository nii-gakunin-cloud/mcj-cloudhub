#!/bin/bash

create_cert() {
    local fqdn="$1"
    local cert_dir="nginx/certs/${fqdn}"
    mkdir -p "${cert_dir}"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${cert_dir}/privkey.pem" \
        -out "${cert_dir}/fullchain.pem" \
        -subj "/CN=${fqdn}"
}

FQDN='localhost'
create_cert $FQDN