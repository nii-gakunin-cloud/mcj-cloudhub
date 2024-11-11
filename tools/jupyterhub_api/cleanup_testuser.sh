#!/bin/bash

delete_ldap () {

    task_id=$(docker service ps $2_openldap --filter "desired-state=running" --format '{{.ID}}')
    container_id=$(docker inspect --format '{{.Status.ContainerStatus.ContainerID}}' $task_id)
    docker exec $container_id ldapdelete -x \
        -H ldap://localhost:1389 \
        -w $3 \
        -D "cn=Manager,dc=jupyterhub,dc=server,dc=sample,dc=jp" \
        "uid=$1,ou=People,dc=jupyterhub,dc=server,dc=sample,dc=jp"
}

delete_home_dir () {
    rm -rf /jupyter/$1
}

delete_jupyterhub_user () {
    curl -X DELETE http://localhost:8000/hub/api/users/$1 \
        -H "Authorization: token $2"
}

# username, uidnum, gidnum, servicename, jupyterhub token, ldap passord
delete_ldap $1 $4 $6
delete_home_dir $1
delete_jupyterhub_user $1 $5
