import copy

from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPNoSuchObjectResult

class ldapClient():
    ldap_base_dn = 'ou=People,dc=jupyterhub,dc=server,dc=sample,dc=jp'
    def __init__(self, host, manager_dn, password):
        self.server = Server(host, get_info=ALL)
        self.conn = Connection(
            host,
            manager_dn,
            password=password,
            read_only=False,
            raise_exceptions=True,
        )

    def search_user(self, username, attributes: list = None):
        self.conn.bind()
        try:
            self.conn.search(
                f'uid={username},{self.ldap_base_dn}',
                '(objectClass=*)',
                attributes=attributes,
            )
            return copy.deepcopy(self.conn.entries)
        except LDAPNoSuchObjectResult:
            return
        finally:
            try:
                self.conn.unbind()
            except Exception:
                pass

    def add_user(self, dn, object_class=None, attributes=None):
        self.conn.bind()
        try:
            self.conn.add(
                dn,
                object_class,
                attributes,
            )
        finally:
            try:
                self.conn.unbind()
            except Exception:
                pass

    def update_user(self, user_name: str, params: dict):
        self.conn.bind()
        try:
            self.conn.modify(
                f'uid={user_name},{self.ldap_base_dn}',
                params,
            )
        finally:
            try:
                self.conn.unbind()
            except Exception:
                pass

