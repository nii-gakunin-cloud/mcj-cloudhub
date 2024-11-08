#!/bin/bash

create_ldif () {

    ldif=$(cat <<- EOM
dn: uid=$1,ou=People,dc=jupyterhub,dc=server,dc=sample,dc=jp
objectclass: posixAccount
objectclass: inetOrgPerson
uid: $1
cn: $1
sn: $1
uidNumber: $2
gidNumber: $3
homeDirectory: /home/$1
loginShell: /bin/bash
userPassword: testuser
mail: $1@example.com
EOM
    )

    echo "$ldif" > /srv/jupyterhub/jupyterhub/ldap/ldifs/tmp.ldif
    task_id=$(docker service ps $4_openldap --filter "desired-state=running" --format '{{.ID}}')
    container_id=$(docker inspect --format '{{.Status.ContainerStatus.ContainerID}}' $task_id)
    docker exec $container_id ldapadd -x \
        -H ldap://localhost:1389 \
        -D "cn=Manager,dc=jupyterhub,dc=server,dc=sample,dc=jp" \
        -w $5 \
        -f /ldifs/tmp.ldif
}

create_home_dir () {
    mkdir -p /jupyter/$1
    chown "$2":"$3" /jupyter/$1
}

add_user_to_Jupyterhub () {
    curl -X POST http://localhost:8000/hub/api/users/$1 \
        -H "Content-Type: application/json" \
        -H "Authorization: token $2" \
        -d '{"name": "$1"}'
}

# username, uidnum, gidnum, servicename, jupyterhub token, ldap passord
create_ldif $1 $2 $3 $4 $6
create_home_dir $1 $2 $3
add_user_to_Jupyterhub $1 $5
