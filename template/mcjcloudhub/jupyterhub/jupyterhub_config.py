import copy
from enum import Enum
import logging
import os
import pwd
import shutil
import sys
import requests
import yaml

from ldap3 import MODIFY_REPLACE
from lti import confirm_key_exist, get_lms_lti_token, get_course_students_by_moodle_api
from utils import (ldapClient, replace_url, confirm_dir,
                   get_random_password, set_permission_recursive)

IMS_LTI13_FQDN = 'purl.imsglobal.org'
IMS_LTI_CLAIM_BASE = f'https://{IMS_LTI13_FQDN}/spec/lti/claim'
IMS_LTI13_KEY_MEMBERSHIP = f'http://{IMS_LTI13_FQDN}/vocab/lis/v2/membership'
IMS_LTI13_KEY_CUSTOM_PARAMS = f'{IMS_LTI_CLAIM_BASE}/custom'
IMS_LTI13_KEY_MEMBER_ROLES = f'{IMS_LTI_CLAIM_BASE}/roles'
IMS_LTI13_KEY_MEMBER_EXT = f'{IMS_LTI_CLAIM_BASE}/ext'
IMS_LTI13_KEY_MEMBER_CONTEXT = f'{IMS_LTI_CLAIM_BASE}/context'
IMS_LTI13_NRPS_TOKEN_SCOPE = f'https://{IMS_LTI13_FQDN}/spec/lti-nrps/scope/contextmembership.readonly'
IMS_LTI13_NRPS_ASSERT_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'
IMS_LTI13_KEY_NRPS = f'https://{IMS_LTI13_FQDN}/spec/lti-nrps/claim/namesroleservice'

lti_custom_env_prefix = "env_"
lti_custom_container_image_name = "container_image_name"

DEFAULT_IDLE_TIMEOUT = 1800
DEFAULT_CULL_EVERY = 60
DEFAULT_SERVER_MAX_AGE = 0
DEFAULT_COOKIE_MAX_AGE_DAYS = 0.25

# -- logger setting --
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('[%(levelname)s %(asctime)s %(module)s %(funcName)s:%(lineno)d] %(message)s')
handler.setFormatter(log_formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

try:
    # 継承先イメージで配置される予定のクラスをインポート試行
    from custom import get_course_students as get_course_students_custom
    logger.info('[Config] Custom function for getting course students is set.')
except Exception:
    # なければベースを使う
    get_course_students_custom = None


def getenv_required(key: str) -> str:
    """Get required environment variable or raise a clear error."""
    val = os.getenv(key)
    if val is None:
        logger.error('Missing required environment variable: %s', key)
        raise KeyError(f'Missing required environment variable: {key}')
    return val


def getenv_optional(key: str, default=None, cast=None):
    """Get optional env var with default and optional casting."""
    val = os.getenv(key, default)
    if val is None:
        return None
    if cast is not None:
        try:
            return cast(val)
        except Exception:
            logger.warning('Failed to cast env var %s value %r', key, val)
            return val
    return val


jupyterhub_fqdn = getenv_required('JUPYTERHUB_FQDN')
jupyterhub_admin_users = os.getenv('JUPYTERHUB_ADMIN_USERS')
gid_teachers = int(os.getenv('TEACHER_GID', 600))
gid_students = int(os.getenv('STUDENT_GID', 601))

ldap_password = getenv_required('LDAP_ADMIN_PASSWORD')
ldap_server = os.getenv('LDAP_SERVER', 'ldap:1389')
ldap_base = 'dc=jupyterhub,dc=server,dc=sample,dc=jp'
ldap_base_dn = f'ou=People,{ldap_base}'
ldap_admin_username = os.getenv('LDAP_ADMIN_USERNAME', 'Manager')
ldap_manager_dn = f'cn={ldap_admin_username},{ldap_base}'

database_dbhost = getenv_required('DB_HOST')
database_dbname = getenv_required('DB_NAME')
database_username = getenv_required('DB_USER')
database_password = getenv_required('DB_PASSWORD')

# LMS / LTI related envs (optional or required where used)
lms_client_id = os.getenv('LMS_CLIENT_ID')
lms_platform_id = os.getenv('LMS_PLATFORM_ID')

# additional LMS / LTI and runtime envs
get_course_member_method = os.getenv('LTI_METHOD')
lms_api_token = os.getenv('LMS_API_TOKEN')
lti_username_key = os.getenv('LTI_USERNAME_KEY', 'email')

# spawner / image / network
notebook_image = getenv_required('NOTEBOOK_IMAGE')
spawner_class_var = os.getenv('JUPYTERHUB_SPAWNER_CLASS', 'dockerspawner.DockerSpawner')
default_url_var = os.getenv('DEFAULT_URL', '/lab')
docker_network_name = os.getenv('DOCKER_NETWORK_NAME')
nb_node_role = os.getenv('NB_NODE_ROLE', 'manager')

# Paths on host
JUPYTERHUB_DIR_HOST = os.getenv('JUPYTERHUB_DIR_HOST',
                                os.path.join('/srv', 'jupyterhub', 'jupyterhub', 'jupyterhub'))
MCJ_DATA_HOST = os.getenv('MCJ_DATA_HOST',
                          os.path.join(JUPYTERHUB_DIR_HOST, 'mcj-data'))
HOME_DIR_ROOT_HOST = os.path.join(MCJ_DATA_HOST, 'jupyter')
SHARE_DIR_ROOT_HOST = os.path.join(MCJ_DATA_HOST, 'jupytershare')

# Paths in jupyterhub container
JUPYTERHUB_DIR = '/etc/jupyterhub'
USER_CONF_DIR = os.path.join(JUPYTERHUB_DIR, 'conf.d')
# SHARE_DIR_ROOT_JUPYTERHUB = os.getenv('SHARE_DIR_ROOT', '/exchange')
SHARE_DIR_ROOT_JUPYTERHUB = '/jupyterdata'
HOME_DIR_ROOT = os.path.join(SHARE_DIR_ROOT_JUPYTERHUB, 'jupyter')
SHARE_DIR_ROOT = os.path.join(SHARE_DIR_ROOT_JUPYTERHUB, 'jupytershare') # or exchange/jupytershare?
SECRET_DIR = os.path.join(SHARE_DIR_ROOT_JUPYTERHUB, 'secrets')
os.makedirs(SECRET_DIR, exist_ok=True)

# Paths in singleuser container
HOME_DIR_ROOT_SINGLEUSER = os.path.join('/home')
SHARE_DIR_ROOT_SINGLEUSER = os.path.join('/jupytershare')

# 閉じたネットワーク内でLMSと通信を行う場合、サービス名を指定する
# 指定が無い場合、LTI認証で得られたURLを利用する
LMS_URL = os.getenv('LMS_URL')
LMS_SUBDIR = os.getenv('LMS_SUBDIR')
ENABLE_CUSTOM_SETUP_BOOL = str(os.getenv('ENABLE_CUSTOM_SETUP', 'no')).lower() in ('true', 'yes', '1')

email_domain = os.getenv('EMAIL_DOMAIN', 'example.com')

try:
    root_obj = pwd.getpwnam("root")
except KeyError as e:
    logger.error("[Config] Could not find root in passwd.")
    raise e

root_uid_num = int(root_obj[2])
# root_gid_num = int(root_obj[3])

resource_yml_path = os.path.join(JUPYTERHUB_DIR, 'jupyterhub_params.yaml')
if os.path.isfile(os.path.join(USER_CONF_DIR, 'jupyterhub_params.yaml')):
    resource_yml_path = os.path.join(USER_CONF_DIR, 'jupyterhub_params.yaml')
    logger.info('[Config] Custom jupyterhub_params.yaml is set.')

with open(resource_yml_path, 'r', encoding="utf-8") as yml:
    config = yaml.safe_load(yml)

c = get_config() # type: ignore # noqa

c.Authenticator.allow_all = True
c.Authenticator.manage_roles = True

# Enable subdomains and allow iframe for nbgrader
# Ref: https://nbgrader.readthedocs.io/en/stable/configuration/jupyterhub_config.html#enabling-jupyterhub-subdomains
c.JupyterHub.enable_subdomains = True

# cookie max-age (days) is 6 hours
c.JupyterHub.cookie_max_age_days = config.get(
    'cookie_max_age_days', DEFAULT_COOKIE_MAX_AGE_DAYS)
c.JupyterHub.cookie_secret_file = os.path.join(SECRET_DIR,
                                               'jupyterhub_cookie_secret')

if config.get('cull_server') is not None:
    cull_server_idle_timeout = config['cull_server'].get(
        'cull_server_idle_timeout', DEFAULT_IDLE_TIMEOUT)
    cull_server_every = config['cull_server'].get(
        'cull_server_every', DEFAULT_CULL_EVERY)
    cull_server_max_age = config['cull_server'].get(
        'cull_server_max_age', DEFAULT_SERVER_MAX_AGE)
else:
    cull_server_idle_timeout = DEFAULT_IDLE_TIMEOUT
    cull_server_every = DEFAULT_CULL_EVERY
    cull_server_max_age = DEFAULT_SERVER_MAX_AGE
c.JupyterHub.load_roles = []

if cull_server_idle_timeout > 0:
    c.JupyterHub.load_roles.append(
        {
            "name": "jupyterhub-idle-culler-role",
            "scopes": [
                "list:users",
                "read:users:activity",
                "read:servers",
                "delete:servers",
            ],
            "services": ["jupyterhub-idle-culler-service"],
        }
    )
    c.JupyterHub.services = [
        {
            "name": "jupyterhub-idle-culler-service",
            "command": [
                sys.executable,
                "-m", "jupyterhub_idle_culler",
                f"--timeout={cull_server_idle_timeout}",
                f"--cull-every={cull_server_every}",
                f"--max-age={cull_server_max_age}",
            ],
        }
    ]

if 'JUPYTERHUB_CRYPT_KEY' not in os.environ:
    logger.warning(
        "Need JUPYTERHUB_CRYPT_KEY env for persistent auth_state.\n"
        "    export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)"
    )
    c.CryptKeeper.keys = [os.urandom(32)]

# The proxy is in another container
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = 'http://jupyterhub-proxy:8001'

# The Hub should listen on all interfaces,
# so user servers can connect
c.JupyterHub.hub_ip = '0.0.0.0'
# this is the name of the 'service' in docker-compose.yml
c.JupyterHub.hub_connect_ip = 'jupyterhub'
# Initialize processing timeout for spawners.
c.JupyterHub.init_spawners_timeout = 60

# Shutdown active kernels (notebooks) when user logged out.
c.JupyterHub.shutdown_on_logout = True
# Whether to shutdown single-user servers when the Hub shuts down.
# Set False not to interrupt existing server when restart hub, especially in production.
c.JupyterHub.cleanup_servers = False
c.JupyterHub.cleanup_proxy = False

# debug-logging for testing
c.JupyterHub.log_level = logging.DEBUG

# Whole system resource restrictions.
# Maximum number of concurrent named servers that can be created by a user at a time.
c.JupyterHub.named_server_limit_per_user = 1
c.JupyterHub.db_kwargs = {
    'pool_recycle': 300
}

# url for the database. e.g. `sqlite:///jupyterhub.sqlite`
# Use MySQL (mariadb)
c.JupyterHub.db_url = 'mysql+mysqlconnector://{}:{}@{}/{}{}'.format(
    database_username,
    database_password,
    database_dbhost,
    database_dbname,
    '')

# -- Set LTI authenticator --
c.JupyterHub.authenticator_class = "ltiauthenticator.lti13.auth.LTI13Authenticator"

# -- configurations for authenticator --
c.Authenticator.refresh_pre_spawn = True
c.Authenticator.auth_refresh_age = 300
c.Authenticator.enable_auth_state = True
c.Authenticator.manage_groups = True
c.Authenticator.manage_roles = True

# -- configurations for lti1.3 --
# Define issuer identifier of the LMS platform
c.LTI13Authenticator.issuer = lms_platform_id
# Add the LTI 1.3 configuration options
c.LTI13Authenticator.authorize_url = f'{c.LTI13Authenticator.issuer}/mod/lti/auth.php'
# The platform's JWKS endpoint url providing public key sets used to verify the ID token
c.LTI13Authenticator.jwks_endpoint = f'{LMS_URL}/mod/lti/certs.php' if LMS_URL \
                                        else f'{c.LTI13Authenticator.issuer}/mod/lti/certs.php'
token_endpoint = f'{LMS_URL}/mod/lti/token.php' if LMS_URL \
                    else f'{c.LTI13Authenticator.issuer}/mod/lti/token.php'

private_key, public_key = confirm_key_exist(path=SECRET_DIR)

service_teachertools_name = "teachertools"
service_teachertools_port = 8088

c.JupyterHub.services.append(
    {
        'name': service_teachertools_name,
        'url': f'http://0.0.0.0:{service_teachertools_port}',
        'command': [
            sys.executable,
            os.path.join(JUPYTERHUB_DIR,
                         f"service_{service_teachertools_name}",
                         "teachertools.py"),
            '--lms-token-endpoint',
            token_endpoint,
            '--lms-client-id',
            lms_client_id,
            '--lms-platform-id',
            lms_platform_id,
            '--port',
            str(service_teachertools_port),
            '--homedir',
            HOME_DIR_ROOT,
            '--lti-key-pair-path',
            SECRET_DIR,
            '--lms-host',
            LMS_URL,
            '--cookie-secret-file',
            c.JupyterHub.cookie_secret_file,
        ],
        'environment': {'LDAP_PASSWORD': ldap_password,
                        'LDAP_SERVER': ldap_server,
                        'LDAP_MANAGER_DN': ldap_manager_dn,
                        **os.environ}
    }
)
# Permission for service
c.JupyterHub.load_roles.append(
    {
        "name": f"{service_teachertools_name}-role",
        "scopes": [
            "read:users",
            "admin:auth_state",
            "read:roles",
        ],
        "services": [service_teachertools_name],
    }
)

# Use JUPTYERHUB_API_TOKEN for service teacher tools
# Ref: https://discourse.jupyter.org/t/add-scopes-to-jupyterhub-api-token-through-helm-chart-values/18543
c.Spawner.server_token_scopes = [
    "access:servers!server",
    "users:activity!user",
    f"access:services!service={service_teachertools_name}",
]

# The external tool's client id as represented within the platform (LMS)
# use centralized LMS client id
c.LTI13Authenticator.client_id = lms_client_id
# default 'email'
c.LTI13Authenticator.username_key = lti_username_key

# Which spawner to use.
c.JupyterHub.spawner_class = spawner_class_var

# -- configurations for Spawner --
c.Spawner.http_timeout = 300
c.Spawner.default_url = default_url_var
c.Spawner.args.append('--allow-root')

# Allowed Images of Notebook
# use centralized notebook image
c.DockerSpawner.allowed_images = [notebook_image]
# Home directory in container
c.DockerSpawner.notebook_dir = '~'

# Image of Notebook
#c.SwarmSpawner.image = notebook_image
c.DockerSpawner.image = notebook_image

# this is the network name for jupyterhub in docker-compose.yml
# with a leading 'swarm_' that docker-compose adds
c.DockerSpawner.network_name = docker_network_name
c.DockerSpawner.extra_host_config = {
    'network_mode': docker_network_name}
if c.JupyterHub.spawner_class == 'dockerspawner.SwarmSpawner':
    c.SwarmSpawner.extra_placement_spec = {
        'constraints': [f'node.role == {nb_node_role}']}

# For debug
# c.SwarmSpawner.debug = True

# launch timeout
c.DockerSpawner.start_timeout = 300

nrps_token = None


class McjRoles(Enum):

    INSTRUCTOR = 'Instructor'
    LEARNER = 'Learner'

    @classmethod
    def get_values(cls) -> list:
        return [d.value for d in cls]

    @classmethod
    def _parse_roles(cls, lti_roles):
        is_instructor = False
        is_learner = False
        for rolename in lti_roles:
            param_type, role = rolename.split('#')
            if param_type != IMS_LTI13_KEY_MEMBERSHIP:
                continue
            if role == cls.INSTRUCTOR.value:
                is_instructor = True
            elif role == cls.LEARNER.value:
                is_learner = True
        return is_instructor, is_learner

    @classmethod
    def get_user_role(cls, lti_roles):
        is_instructor, is_learner = cls._parse_roles(lti_roles)
        if not is_learner and is_instructor:
            return cls.INSTRUCTOR.value
        return cls.LEARNER.value

    @classmethod
    def is_instructor(cls, lti_roles):
        is_instructor, is_learner = cls._parse_roles(lti_roles)
        return not is_learner and is_instructor


role_config = {
    McjRoles.INSTRUCTOR.value: {
        'cpu_limit': config['resource']['groups']['teacher']['cpu_limit'],
        'mem_limit': config['resource']['groups']['teacher']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['teacher']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['teacher']['mem_guarantee'],
        'gid_num': gid_teachers,
        'login_shell': '/bin/bash',
        'template_dir_name': 'teacher',
    },
    McjRoles.LEARNER.value: {
        'cpu_limit': config['resource']['groups']['student']['cpu_limit'],
        'mem_limit': config['resource']['groups']['student']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['student']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['student']['mem_guarantee'],
        'gid_num': gid_students,
        'login_shell': '/sbin/nologin',
        'template_dir_name': 'student',
    },
}


class McjException(Exception):
    def __init__(self, arg=''):
        self.arg = arg


class InvalidUserInfoException(McjException):
    def __str__(self):
        return (
            f'ERROR: organization_user [{self.arg}]'
        )


class CreateDirectoryException(McjException):
    def __str__(self):
        return (
            f'ERROR: Could not create directory: [{self.arg}]'
        )


class FailedAuthStateHookException(McjException):
    def __str__(self):
        return (
            'ERROR: Failed to auth_state_hook. See the log to get detail.'
        )


def get_user_mounts(course_name: str, role: str, username: str) -> dict:

    mounts = dict()
    mounts[os.path.join(HOME_DIR_ROOT_HOST, username)] = {
        'bind': os.path.join(HOME_DIR_ROOT_SINGLEUSER, username),
        'mode': 'rw',
    }
    mounts[os.path.join(SHARE_DIR_ROOT_HOST, 'class', course_name)] = {
        'bind': os.path.join(SHARE_DIR_ROOT_SINGLEUSER, 'class', course_name),
        'mode': 'rw',
    }
    mounts[os.path.join(SHARE_DIR_ROOT_HOST, 'nbgrader', 'exchange', course_name)] = {
        'bind': os.path.join(SHARE_DIR_ROOT_SINGLEUSER, 'nbgrader', 'exchange', course_name),
        'mode': 'rw',
    }

    if ENABLE_CUSTOM_SETUP_BOOL is True:
        local_lib_dir = os.path.join(SHARE_DIR_ROOT_HOST, course_name,
                                     'opt', 'local')
        local_bin = os.path.join(local_lib_dir, 'bin')
        local_sbin = os.path.join(local_lib_dir, 'sbin')

        local_lib_dir_container = os.path.join('/opt', 'local')
        local_bin_container = os.path.join(local_lib_dir_container, 'bin')
        local_sbin_container = os.path.join(local_lib_dir_container, 'sbin')

        if role == McjRoles.INSTRUCTOR.value:
            mounts[local_sbin] = {
                'bind': local_sbin_container,
                'mode': 'rw',
            }
            mounts[local_bin] = {
                'bind': local_bin_container,
                'mode': 'rw',
            }
        else:
            mounts[local_sbin] = {
                'bind': local_sbin_container,
                'mode': 'ro',
            }
            mounts[local_bin] = {
                'bind': local_bin_container,
                'mode': 'ro',
            }
    return mounts


def confirm_share_dir(role, user_name,
                      uid_num, course):

    course_share_dir_root = os.path.join(SHARE_DIR_ROOT, 'class')
    share_path = os.path.join(course_share_dir_root, course, 'share')
    submit_root = os.path.join(course_share_dir_root, course, 'submit')
    submit_dir = os.path.join(course_share_dir_root, course, 'submit',
                              user_name)

    confirm_dir(submit_root, mode=0o0755, uid=root_uid_num,
                gid=gid_teachers)
    confirm_dir(share_path, mode=0o0775, uid=root_uid_num,
                gid=gid_teachers)

    local_lib_dir = os.path.join(SHARE_DIR_ROOT, course,
                                 'opt', 'local')
    if role == McjRoles.INSTRUCTOR.value:

        confirm_dir(course_share_dir_root, mode=0o0775, uid=root_uid_num,
                    gid=root_uid_num)
        confirm_dir(course_share_dir_root, mode=0o0775, uid=root_uid_num,
                    gid=gid_teachers)
        confirm_dir(submit_dir, mode=0o0750, uid=uid_num,
                    gid=root_uid_num)
        confirm_dir(os.path.join(local_lib_dir, 'bin'),
                    mode=0o0755, uid=uid_num,
                    gid=-1)
        confirm_dir(os.path.join(local_lib_dir, 'sbin'),
                    mode=0o0755, uid=uid_num,
                    gid=-1)

    else:
        confirm_dir(submit_dir, mode=0o0750, uid=uid_num,
                    gid=gid_teachers)


def get_nrps_token():
    return get_lms_lti_token(IMS_LTI13_NRPS_TOKEN_SCOPE,
                             jupyterhub_fqdn,
                             private_key,
                             token_endpoint,
                             lms_client_id)


def get_course_students_by_nrps(url, default_key='user_id'):

    global nrps_token
    if nrps_token is None:
        nrps_token = get_nrps_token()
        logger.info('Created LMS access token')
    headers = {'Authorization': f'Bearer {nrps_token}'}
    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )
    if response.status_code == 401:

        logger.info('LMS access token expired')
        nrps_token = get_nrps_token()
        logger.info('LMS access token successfully recreated')
        headers = {'Authorization': f'Bearer {nrps_token}'}
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

    students = list()
    for member in response.json().get('members'):
        if not member['status'] == 'Active' or 'Learner' not in member['roles']:
            continue

        user_id = member.get('ext_user_username', member.get(default_key))

        students.append(
            dict(
                id=user_id,
                first_name=member.get('given_name'),
                last_name=member.get('family_name'),
                email=member.get('email'),
                lms_user_id=member['user_id']))
    return students


def confirm_dirs(course_name,
                 role,
                 user_name,
                 user_uid_num,
                 groupid,
                 students):

    exchange_root_path = os.path.join(SHARE_DIR_ROOT, 'nbgrader',
                                      'exchange')
    exchange_course_path = os.path.join(exchange_root_path, course_name)
    exchange_inbound_path = os.path.join(exchange_course_path, 'inbound')
    exchange_outbound_path = os.path.join(exchange_course_path, 'outbound')
    exchange_feedback_path = os.path.join(exchange_course_path, 'feedback')

    user_home = os.path.join(HOME_DIR_ROOT, user_name)
    home_dir_base = os.path.join(JUPYTERHUB_DIR,
                                 'home',
                                 role_config[role]['template_dir_name'])

    # ホームディレクトリ作成
    confirm_dir(user_home, mode=0o755, uid=user_uid_num, gid=groupid)
    confirm_dir(exchange_root_path, mode=0o0755, uid=root_uid_num,
                gid=gid_teachers)

    if role == McjRoles.INSTRUCTOR.value:

        # README.md: 存在しなければ作成
        shutil.copy(os.path.join(home_dir_base, 'README.md'),
                    user_home)
        # teacher_tools: 存在しなければ作成
        tools_dir = os.path.join(user_home, 'teacher_tools')
        if not os.path.isdir(tools_dir):
            shutil.copytree(os.path.join(home_dir_base, 'teacher_tools'),
                            tools_dir)
            set_permission_recursive(tools_dir, uid=user_uid_num)

        confirm_dir(exchange_course_path, mode=0o0755, uid=user_uid_num,
                    gid=gid_teachers)
        confirm_dir(exchange_inbound_path, mode=0o0733, uid=user_uid_num,
                    gid=gid_students)
        confirm_dir(exchange_outbound_path, mode=0o0755, uid=user_uid_num,
                    gid=gid_students)
        confirm_dir(exchange_feedback_path, mode=0o0711, uid=user_uid_num,
                    gid=gid_students)

        instructor_root_path = os.path.join(user_home, 'nbgrader')
        instructor_log_file = os.path.join(instructor_root_path,
                                           'nbgrader.log')
        course_dir = os.path.join(instructor_root_path, course_name)
        course_autograded_dir = os.path.join(course_dir, 'autograded')
        course_release_dir = os.path.join(course_dir, 'release')
        course_source_dir = os.path.join(course_dir, 'source')
        course_submitted_dir = os.path.join(course_dir, 'submitted')
        course_nbgrader_config = os.path.join(course_dir, 'nbgrader_config.py')
        cource_header_file = os.path.join(course_source_dir, 'header.ipynb')
        cource_autotests_yml = os.path.join(course_dir, 'autotests.yml')

        config_template_file = os.path.join(home_dir_base,
                                            'nbgrader_config.py')
        header_template_file = os.path.join(home_dir_base,
                                            'header.ipynb')
        autotests_yml = os.path.join(home_dir_base, 'autotests.yml')

        confirm_dir(instructor_root_path, uid=user_uid_num,
                    gid=gid_teachers, mode=0o0755)
        confirm_dir(course_dir, uid=user_uid_num, gid=gid_teachers,
                    mode=0o0755)
        confirm_dir(course_autograded_dir, mode=0o0755, uid=user_uid_num,
                    gid=groupid)
        confirm_dir(course_release_dir, mode=0o0755, uid=user_uid_num,
                    gid=groupid)
        confirm_dir(course_source_dir, mode=0o2755, uid=user_uid_num,
                    gid=groupid)
        confirm_dir(course_submitted_dir, mode=0o0755, uid=user_uid_num,
                    gid=groupid)

        with open(config_template_file, encoding="utf-8") as f1:
            target_lines = f1.read()

        target_lines = target_lines.replace(
            'NBG_STUDENTS = []', f"NBG_STUDENTS = {str(students)}")

        # ログインするコースに合わせて毎回再作成するもの（システム管理）
        if os.path.exists(course_nbgrader_config):
            os.remove(course_nbgrader_config)

        with open(course_nbgrader_config, mode="w", encoding="utf-8") as f2:
            f2.write(target_lines)

        os.chown(course_nbgrader_config, user_uid_num, groupid)
        os.chmod(course_nbgrader_config, 0o0644)

        # コース毎ごとのディレクトリ配下にあるものは、存在しない場合にのみ作成
        if not os.path.isfile(cource_header_file):

            shutil.copyfile(header_template_file, cource_header_file)
            os.chown(cource_header_file, user_uid_num, groupid)
            os.chmod(cource_header_file, 0o0644)

        if not os.path.isfile(cource_autotests_yml):

            shutil.copyfile(autotests_yml, cource_autotests_yml)
            os.chown(cource_autotests_yml, user_uid_num, groupid)
            os.chmod(cource_autotests_yml, 0o0644)

        if os.path.exists(instructor_log_file):
            fp = open(instructor_log_file, 'r+', encoding="utf-8")
            fp.truncate(0)
            fp.close()
            os.chown(instructor_log_file, user_uid_num, groupid)
            os.chmod(instructor_log_file, 0o0644)


def auth_state_hook(spawner, auth_state):

    lms_username = auth_state[IMS_LTI13_KEY_MEMBER_EXT]['user_username']
    lms_course_shortname = auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['label']
    lms_role = McjRoles.get_user_role(auth_state[IMS_LTI13_KEY_MEMBER_ROLES])
    homedir_singleuser = os.path.join(HOME_DIR_ROOT_SINGLEUSER, lms_username)
    uid_num = int(auth_state['sub']) + 1000
    gid_num = role_config[lms_role]['gid_num']

    ldapconn = ldapClient(ldap_server, ldap_manager_dn, ldap_password)
    search_result = ldapconn.search_user(lms_username, ['uidNumber'])

    lti_custom_params = auth_state[IMS_LTI13_KEY_CUSTOM_PARAMS]

    if search_result is None:
        ldapconn.add_user(
            f'uid={lms_username},{ldap_base_dn}',
            ['posixAccount', 'inetOrgPerson'],
            {
                'uid': lms_username,
                'cn': lms_username,
                'sn': lms_username,
                'uidNumber': uid_num,
                'gidNumber': gid_num,
                'homeDirectory': homedir_singleuser,
                'loginShell': role_config[lms_role]['login_shell'],
                'userPassword': get_random_password(12),
                'mail': f'{lms_username}@{email_domain}',
            },
        )
    else:
        ldapconn.update_user(lms_username,
                             {'gidNumber': [(MODIFY_REPLACE, [gid_num])]})

    students = list()
    if get_course_member_method == 'moodle_api':
        students = get_course_students_by_moodle_api(
            f'{c.LTI13Authenticator.issuer}/webservice/rest/server.php',
            lms_api_token,
            auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['id'])
    elif get_course_students_custom is not None:
        students = get_course_students_custom(
            auth_state,
            lms_course_shortname)
    else:
        context_memberships_url = auth_state[IMS_LTI13_KEY_NRPS]['context_memberships_url']
        if LMS_URL:
            context_memberships_url = replace_url(context_memberships_url,
                                                  LMS_URL, LMS_SUBDIR)
        students = get_course_students_by_nrps(
            context_memberships_url,
            default_key=c.LTI13Authenticator.username_key)

    confirm_dirs(
        lms_course_shortname, lms_role, lms_username,
        uid_num, gid_num,
        students)

    confirm_share_dir(
        lms_role,
        lms_username,
        uid_num,
        lms_course_shortname,
    )

    spawner.environment = {
        'MOODLECOURSE': lms_course_shortname,
        'COURSEROLE': lms_role,
        'TZ': 'Asia/Tokyo',
        'TEACHER_GID': gid_teachers,
        'STUDENT_GID': gid_students,
        'JUPYTERHUB_FQDN': jupyterhub_fqdn,
        'PATH': f'{homedir_singleuser}/.local/bin:' +
                f'{homedir_singleuser}/bin:/usr/local/bin:/usr/local/sbin:' +
                '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin:' +
                '/tmp/pip/bin',
        'NB_USER': lms_username,
        'PWD': homedir_singleuser,
        'NB_UID': uid_num,
        'NB_GID': gid_num,
        'HOME': homedir_singleuser,
        'CHOWN_HOME': 'yes',
        'CHOWN_EXTRA': homedir_singleuser,
        'CHOWN_EXTRA_OPTS': '-R',
    }
    for key, value in lti_custom_params.items():
        if lti_custom_env_prefix in key:
            spawner.environment[key.replace('env_', '')] = value
    spawner.image = lti_custom_params.get(lti_custom_container_image_name,
                                          os.environ['NOTEBOOK_IMAGE'])

    spawner.environment['ENABLE_CUSTOM_SETUP'] = os.getenv('ENABLE_CUSTOM_SETUP', 'no')

    spawner.cpu_limit = role_config[lms_role]['cpu_limit']
    spawner.mem_limit = role_config[lms_role]['mem_limit']
    spawner.cpu_guarantee = role_config[lms_role]['cpu_guarantee']
    spawner.mem_guarantee = role_config[lms_role]['mem_guarantee']
    spawner.user.name = lms_username
    spawner.user_id = uid_num
    spawner.group_id = gid_num
    spawner.volumes = get_user_mounts(lms_course_shortname, lms_role, spawner.user.name)


def post_auth_hook(lti_authenticator, handler, authentication):
    """ An optional hook function that to do some bootstrapping work during authentication.

    Args:
        handler (tornado.web.RequestHandler): the current request handler
        authentication (dict): User authentication data dictionary. Contains the
            username ('name'), admin status ('admin'), and auth state dictionary ('auth_state').
    Returns:
        Authentication (dict):
            The hook must always return the authentication dict
    """

    updated_auth_state = copy.deepcopy(authentication)
    lms_user_name = authentication['auth_state'][IMS_LTI13_KEY_MEMBER_EXT]['user_username']
    if jupyterhub_admin_users is not None and lms_user_name in jupyterhub_admin_users:
        updated_auth_state['admin'] = True
    # groupはログイン中のコース、roleがJupyterhubに対する権限
    course_name = updated_auth_state['auth_state'][IMS_LTI13_KEY_MEMBER_CONTEXT]['label']
    updated_auth_state['name'] = lms_user_name
    updated_auth_state['groups'] = [course_name]

    if 'roles' not in updated_auth_state:
        updated_auth_state['roles'] = list()

    # デフォルトのuserは使えない？
    updated_auth_state['roles'].append({'name': 'user'})

    role_user_common = {
        'name': 'self',
    #    'scopes': ['users!user=self']
    }
    updated_auth_state['roles'].append(role_user_common)

    is_t = McjRoles.is_instructor(authentication['auth_state'][IMS_LTI13_KEY_MEMBER_ROLES])
    if is_t:
        updated_auth_state['groups'].append('teacher')

        role_course_teacher = {
            'name': f'instructor-{course_name}',
            'scopes': [
                'admin-ui',
                f'list:users!group={course_name}',
                f'admin:servers!group={course_name}',
                f"access:servers!group={course_name}",
            ]}
        role_instructor_common = {
            'name': 'instructor',
            'scopes': ['access:services',
                       f"access:services!service={service_teachertools_name}"]
        }
        updated_auth_state['roles'].append(role_instructor_common)
        updated_auth_state['roles'].append(role_course_teacher)

    return updated_auth_state


c.DockerSpawner.auth_state_hook = auth_state_hook
c.Authenticator.post_auth_hook = post_auth_hook
