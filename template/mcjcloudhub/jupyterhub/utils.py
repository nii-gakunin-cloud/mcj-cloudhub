import copy
import os
import secrets
import string
from urllib.parse import urlparse

from ldap3 import Server, Connection, ALL
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


def replace_url(url: str, new_url: str, subdir: str = None):
    current = urlparse(url)
    new = urlparse(new_url)
    _url = current._replace(scheme=new.scheme,
                            netloc=new.netloc)
    if subdir is not None:
        path = '/' + '/'.join(_url.path.split('/')[2:]) if subdir == _url.path.split('/')[1] else _url.path
        _url = current._replace(scheme=new.scheme,
                                netloc=new.netloc,
                                path=path)
    return _url.geturl()


def confirm_dir(path: str, mode: int = 0o700, uid: int = -1, gid: int = -1) -> None:
    os.makedirs(path, exist_ok=True)
    os.chmod(path, mode=mode)
    os.chown(path, uid, gid)


def get_random_password(size: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(size))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            break
    return password


def set_permission_recursive(path: str, mode: int | None = None,
                             uid: int = -1, gid: int = -1) -> None:
    for root, dirs, files in os.walk(path):
        for d in dirs:
            p = os.path.join(root, d)
            if mode is not None:
                os.chmod(p, mode)
            os.chown(p, uid, gid)

        for f in files:
            p = os.path.join(root, f)
            if mode is not None:
                os.chmod(p, mode)
            os.chown(p, uid, gid)
