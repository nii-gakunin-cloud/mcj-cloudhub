#!/bin/bash

docker network create jupyterhub_public
docker buildx build ./notebook/image/notebook-6.5.4 -t mcj-cloudhub-nb:notebook-6.5.4

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout ./jupyterhub/nginx/certs/privkey.pem \
  -out ./jupyterhub/nginx/certs/fullchain.pem \
  -subj "/CN=localhost"
docker buildx build -f ./docker-compose.yml
docker compose up -d