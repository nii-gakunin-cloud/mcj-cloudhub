#!/bin/sh

: ${NFS_SERVER:?"NFS_SERVER must be set!"}

grep -wq /mnt/nfs /etc/fstab
if [ $? != 0 ]; then
cat >> /etc/fstab <<EOF
${NFS_SERVER}:/ /mnt/nfs nfs rw,_netdev,auto 0 0
EOF
fi

grep -wq /jupytershare /etc/fstab
if [ $? != 0 ]; then
cat >> /etc/fstab <<EOF
/mnt/nfs/jupytershare /jupytershare none bind 0 0
EOF
fi

grep -wq /home /etc/fstab
if [ $? != 0 ]; then
cat >> /etc/fstab <<EOF
/mnt/nfs/home /home none bind 0 0
EOF
fi