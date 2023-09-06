ARG BASE_IMAGE=rterayama1103/cwhnfsmodify-common:0.1.2
# hadolint ignore=DL3006
FROM $BASE_IMAGE

COPY etc /etc/
RUN systemctl enable nfs-server nfs-idmapd coursewarehub-dirs