#!/bin/sh
set -e

: ${NFS_SERVER:?"NFS_SERVER must be set!"}

cat >> /etc/fstab <<EOF
${NFS_SERVER}:/ /mnt/nfs nfs rw,_netdev,auto 0 0
${NFS_SERVER}:/home /home nfs rw,_netdev,auto 0 0
${NFS_SERVER}:/jupytershare /jupytershare nfs rw,_netdev,auto 0 0
EOF
