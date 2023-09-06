ARG BASE_IMAGE=rterayama1103/cwhnfsmodify-common:0.1.2
# hadolint ignore=DL3006
FROM $BASE_IMAGE

COPY etc /etc/

RUN mkdir -p /mnt/nfs /jupytershare \
 && chmod 0777 /home /jupytershare \
 && systemctl enable rpcbind
