#!/bin/sh

: ${NFS_SERVER:?"NFS_SERVER must be set!"}

cat > /etc/fstab <<EOF
${NFS_SERVER}:/ /mnt/nfs nfs rw,_netdev,auto 0 0
/mnt/nfs/jupytershare /jupytershare none bind 0 0
/mnt/nfs/home /home none bind 0 0
EOF
