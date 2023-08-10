def get_univercity_role(username):
    """大学での教師/学生を判別する処理

        Args:
            username(String): Moodleでのユーザ名 ex.'admin'

        Returns:
            uidNumberとroleをキーに持つ、dict型を返す。
            例. {'uidNumber': uidNumber, 'role': 'Learner'}
            roleは必須。'Instructor'または'Learner' を返す。
            uidNumberは任意。設定が無い場合（LDAPでない場合を含む）、項目自体無しもしくは-1を返す。

    """

#     from ldap3 import Server, Connection, ALL
#     import sys
#     global_ldap_server = '172.30.2.120:1389'
#     global_ldap_base_dn = 'ou=People,dc=ldap,dc=server,dc=sample,dc=jp'
#     global_ldap_password = 'PassWordDesu'
#     univserver = Server(global_ldap_server, get_info=ALL)

#     if len(global_ldap_password) >= 5:
#         univconn = Connection(univserver, password=global_ldap_password)
#     else:
#         univconn = Connection(univserver)

#     conn_result = univconn.bind()
#     # if connection to university ldap server failed.
#     if not conn_result:
#         sys.stderr.write("Cannot connect to ldap server in yuniversity.\n")
#         return
#     # if connection to university ldap server succeeded.
#     else:
#         search_result = univconn.search(
#             f'uid={username},{global_ldap_base_dn}',
#             '(objectclass=*)',
#             attributes=['uidNumber','gidNumber','homeDirectory'])

#         # when user is not a staff/student in university.
#         if not search_result:
#             sys.stderr.write("Error: User [" + username + "] does not exist in university ldap.\n")
#             return

#     # get properies for user.
#     uidNumber = univconn.entries[0]['uidNumber'].value
#     gidNumber = univconn.entries[0]['gidNumber'].value
#     homeDirectory = univconn.entries[0]['homeDirectory'].value

#     if gidNumber == uidNumber and not homeDirectory.startswith('/st'):
#         return {'uidNumber': uidNumber, 'role': 'Instructor'}

#     return {'uidNumber': uidNumber, 'role': 'Learner'}