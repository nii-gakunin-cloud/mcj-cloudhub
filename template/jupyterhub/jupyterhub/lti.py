import jwt
import os
import requests
import time
import urllib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


IMS_LTI13_NRPS_ASSERT_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'


def generate_keypair(privkey=None) -> bytes:

    # 鍵の生成
    private_key = privkey if privkey is not None else rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Public key
    public_key = private_key.public_key()

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    return private_key_pem, public_key_pem


def confirm_key_exist(path='/etc/jupyterhub'):
    """キーペアファイルがあれば読み取り、無ければ作成する
    LMSの外部ツール設定でツールの公開鍵を設定する必要があり、
    Jupyterhub再起動の度に変更しないためにファイル出力して保存する。
    """
    pubkey = os.path.join(path, 'lti_pubkey.pem')
    privkey = os.path.join(path, 'lti_privkey.pem')
    if os.path.isfile(pubkey) and \
       os.path.isfile(privkey):
        with open(privkey, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
        # 未使用
        with open(pubkey, "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read(),
            )
    else:
        private_key = None
        if os.path.isfile(privkey):
            with open(privkey, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                )
        private_key, public_key = generate_keypair(private_key)
        with open(pubkey, "w+b") as f:
            f.write(public_key)
        with open(privkey, "w+b") as f:
            f.write(private_key)
        os.chmod(privkey, 0o0400)

    return private_key, public_key


def create_lti_jwt(tool_url, private_key, token_endpoint, client_id):

    current_unix_time = int(time.time())
    token_value = {
        "iss": tool_url,
        "iat": current_unix_time,
        #"exp": current_unix_time + 60 * 60 * 24 * 100,
        "exp": current_unix_time + 60,
        "aud": token_endpoint,
        "sub": client_id
    }
    print(f'Expire: {current_unix_time + 60 * 10}')
    return jwt.encode(
        token_value, private_key, algorithm="RS256")


def get_lms_lti_token(scopes: str | list, tool_url, private_key, token_endpoint, client_id) -> str:

    # scopeはスペース区切りで指定する
    if str == type(scopes):
        _scopes = scopes
    elif list == type(scopes) or tuple == type(scopes):
        _scopes = ' '.join(scopes)
    else:
        _scopes = scopes

    jwt = create_lti_jwt(tool_url, private_key, token_endpoint, client_id)

    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': IMS_LTI13_NRPS_ASSERT_TYPE,
        'client_assertion': jwt,
        'scope': _scopes,
    }
    data = urllib.parse.urlencode(data)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    response = requests.post(
        token_endpoint,
        headers=headers,
        data=data,
        timeout=30
    )

    if 200 != response.status_code:
        print(response.text)
        raise Exception("Failed to get nrps token from LMS. Public key in outer tool settings in LMS may be wrong")

    return response.json()['access_token']

