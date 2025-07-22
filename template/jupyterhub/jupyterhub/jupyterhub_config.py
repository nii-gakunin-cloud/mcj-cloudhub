import copy
from enum import Enum
import logging
import os
import pwd
import secrets
import shutil
import string
import sys
import requests
import yaml
from ldap3 import MODIFY_REPLACE

from lms_web_service import get_course_students_by_lms_api
from lti import confirm_key_exist, get_lms_lti_token
from utils import ldapClient

LOG_FORMAT = '[%(levelname)s %(asctime)s %(module)s %(funcName)s:%(lineno)d] %(message)s'
CONTEXTLEVEL_COURSE = 50
IMS_LTI13_FQDN = 'purl.imsglobal.org'
IMS_LTI_CLAIM_BASE = f'https://{IMS_LTI13_FQDN}/spec/lti/claim'
IMS_LTI13_KEY_MEMBERSHIP = f'http://{IMS_LTI13_FQDN}/vocab/lis/v2/membership'
IMS_LTI13_KEY_MEMBER_ROLES = f'{IMS_LTI_CLAIM_BASE}/roles'
IMS_LTI13_KEY_MEMBER_EXT = f'{IMS_LTI_CLAIM_BASE}/ext'
IMS_LTI13_KEY_MEMBER_CONTEXT = f'{IMS_LTI_CLAIM_BASE}/context'
IMS_LTI13_NRPS_TOKEN_SCOPE = f'https://{IMS_LTI13_FQDN}/spec/lti-nrps/scope/contextmembership.readonly'
IMS_LTI13_NRPS_ASSERT_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'
IMS_LTI13_KEY_NRPS = f'https://{IMS_LTI13_FQDN}/spec/lti-nrps/claim/namesroleservice'

DEFUALT_IDLE_TIMEOUT = 1800
DEFUALT_CULL_EVERY = 60
DEFUALT_SERVER_MAX_AGE = 0
DEFUALT_COOKIE_MAX_AGE_DAYS = 0.25

HOME_DIR_ROOT = '/home'
SHARE_DIR_ROOT = '/jupytershare'

# -- logger setting --
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(log_formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

jupyterhub_fqdn = os.environ['JUPYTERHUB_FQDN']
jupyterhub_admin_users = os.getenv('JUPYTERHUB_ADMIN_USERS')
gid_teachers = int(os.getenv('TEACHER_GID', 600))
gid_students = int(os.getenv('STUDENT_GID', 601))

ldap_password = os.environ['LDAP_PASSWORD']
ldap_server = os.getenv('LDAP_SERVER', 'ldap:1389')
ldap_base_dn = 'ou=People,dc=jupyterhub,dc=server,dc=sample,dc=jp'
ldap_manager_dn = f'cn={os.getenv("LDAP_ADMIN", "Manager")},'\
                    'dc=jupyterhub,dc=server,dc=sample,dc=jp'

database_dbhost = os.getenv('DB_HOST', 'mariadb')
database_dbname = os.getenv('DB_NAME', 'jupyterhub')
database_username = os.getenv('DB_USER', 'jupyter')
database_password = os.environ['DB_PASSWORD']

get_course_member_method = os.getenv('LTI_METHOD')
lms_api_token = os.getenv('LMS_API_TOKEN')

HOME_DIR_ROOT_HOST = os.environ['HOME_DIR_ROOT']
SHARE_DIR_ROOT_HOST = os.environ['SHARE_DIR_ROOT']
skelton_directory = os.path.join(HOME_DIR_ROOT_HOST, 'skelton')
email_domain = os.getenv('EMAIL_DOMAIN', 'example.com')

with open('/etc/jupyterhub/jupyterhub_params.yaml', 'r', encoding="utf-8") as yml:
    config = yaml.safe_load(yml)

c = get_config() # type: ignore # noqa

c.Authenticator.allow_all = True
c.Authenticator.manage_roles = True

# cookie max-age (days) is 6 hours
c.JupyterHub.cookie_max_age_days = config.get(
    'cookie_max_age_days', DEFUALT_COOKIE_MAX_AGE_DAYS)
c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/jupyterhub_cookie_secret'

if config.get('cull_server') is not None:
    cull_server_idle_timeout = config['cull_server'].get(
        'cull_server_idle_timeout', DEFUALT_IDLE_TIMEOUT)
    cull_server_every = config['cull_server'].get(
        'cull_server_every', DEFUALT_CULL_EVERY)
    cull_server_max_age = config['cull_server'].get(
        'cull_server_max_age', DEFUALT_SERVER_MAX_AGE)
else:
    cull_server_idle_timeout = DEFUALT_IDLE_TIMEOUT
    cull_server_every = DEFUALT_CULL_EVERY
    cull_server_max_age = DEFUALT_SERVER_MAX_AGE
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
c.JupyterHub.cleanup_servers = True

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

# -- configurations for lti1.3 --
# Define issuer identifier of the LMS platform
c.LTI13Authenticator.issuer = os.getenv('LMS_PLATFORM_ID')
# Add the LTI 1.3 configuration options
c.LTI13Authenticator.authorize_url = f'{c.LTI13Authenticator.issuer}/mod/lti/auth.php'
# The platform's JWKS endpoint url providing public key sets used to verify the ID token
c.LTI13Authenticator.jwks_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/certs.php'
token_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/token.php'
private_key, public_key = confirm_key_exist()

port = 8088
c.JupyterHub.services.append(
    {
        'name': 'teachertools',
        'url': f'http://0.0.0.0:{port}',
        'command': [
            sys.executable,
            "/etc/jupyterhub/service-teachertools/teachertools.py",
            '--lms-token-endpoint',
            token_endpoint,
            '--lms-client-id',
            os.getenv('LMS_CLIENT_ID'),
            '--port',
            str(port),
            '--homedir',
            HOME_DIR_ROOT_HOST,
        ],
        'environment': {'LDAP_PASSWORD': os.environ['LDAP_PASSWORD'],
                        'LDAP_SERVER': ldap_server}
    }
)

c.JupyterHub.load_roles.append(
    {
        "name": "teachertools-service-role",
        "scopes": [
            "read:users",
            "admin:auth_state",
            "read:roles",
        ],
        "services": ["teachertools"],
    }
)

# The external tool's client id as represented within the platform (LMS)
c.LTI13Authenticator.client_id = os.getenv('LMS_CLIENT_ID')
# default 'email'
c.LTI13Authenticator.username_key = os.getenv('LTI_USERNAME_KEY', 'email')

# Use SwarmSpawner.
c.JupyterHub.spawner_class = 'dockerspawner.SwarmSpawner'

# -- configurations for Spawner --
c.Spawner.http_timeout = 300
c.Spawner.default_url = os.getenv('DEFAULT_URL', "/lab")
c.Spawner.args.append('--allow-root')

# Allowed Images of Notebook
#c.DockerSpawner.allowed_images = [os.environ['NOTEBOOK_IMAGE']]
c.DockerSpawner.allowed_images = [f"{os.environ['NOTEBOOK_IMAGE']}"]
# Home directory in container
c.DockerSpawner.notebook_dir = '~'

# Image of Notebook
#c.SwarmSpawner.image = os.environ['NOTEBOOK_IMAGE']
c.SwarmSpawner.image = f"{os.environ['NOTEBOOK_IMAGE']}"

# this is the network name for jupyterhub in docker-compose.yml
# with a leading 'swarm_' that docker-compose adds
c.SwarmSpawner.network_name = os.getenv('DOCKER_NETWORK_NAME')
c.SwarmSpawner.extra_host_config = {
    'network_mode': os.getenv('DOCKER_NETWORK_NAME')}
c.SwarmSpawner.extra_placement_spec = {
    'constraints': [f'node.role == {os.getenv("NB_NODE_ROLE", "manager")}']}

# For debug
# c.SwarmSpawner.debug = True

# launch timeout
c.SwarmSpawner.start_timeout = 300

nrps_token = None


class McjRoles(Enum):

    INSTRUCTOR = 'Instructor'
    LEARNER = 'Learner'

    @classmethod
    def get_values(cls) -> list:
        return [d.value for d in cls]

    @classmethod
    def get_user_role(cls, lti_roles):
        """role判定

        Instructor&Learner -> Learner
        Learner -> Learner
        Instructor -> Instructor
        """

        is_instructor = False
        is_learner = False
        for rolename in lti_roles:
            param_type, role = rolename.split('#')
            if not param_type == IMS_LTI13_KEY_MEMBERSHIP:
                continue
            if role == cls.INSTRUCTOR.value:
                is_instructor = True
            elif role == cls.LEARNER.value:
                is_learner = True

        if not is_learner and is_instructor:
            return cls.INSTRUCTOR.value
        else:
            return cls.LEARNER.value

    @classmethod
    def is_instructor(cls, lti_roles):
        """role判定

        Instructor&Learner -> Learner
        Learner -> Learner
        Instructor -> Instructor
        """

        is_instructor = False
        is_learner = False
        for rolename in lti_roles:
            param_type, role = rolename.split('#')
            if not param_type == IMS_LTI13_KEY_MEMBERSHIP:
                continue
            if role == cls.INSTRUCTOR.value:
                is_instructor = True
            elif role == cls.LEARNER.value:
                is_learner = True

        return not is_learner and is_instructor


role_config = {
    McjRoles.INSTRUCTOR.value: {
        'cpu_limit': config['resource']['groups']['teacher']['cpu_limit'],
        'mem_limit': config['resource']['groups']['teacher']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['teacher']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['teacher']['mem_guarantee'],
        'gid_num': gid_teachers,
        'login_shell': '/bin/bash',
        'template_dir_name': 'teachers',
    },
    McjRoles.LEARNER.value: {
        'cpu_limit': config['resource']['groups']['student']['cpu_limit'],
        'mem_limit': config['resource']['groups']['student']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['student']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['student']['mem_guarantee'],
        'gid_num': gid_students,
        'login_shell': '/sbin/nologin',
        'template_dir_name': 'students',
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


def confirm_dir(path, mode=0o700, uid=-1, gid=-1):

    os.makedirs(path, exist_ok=True)
    os.chmod(path, mode=mode)
    os.chown(path, uid, gid)


def change_owner(homePath, uid, gid):
    for root, dirs, files in os.walk(homePath):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
    os.chown(homePath, uid, gid)


def get_random_password(size=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(size))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            break
    return password


def set_permission_recursive(path: str, mode = None,
                             uid: int = -1, gid: int = -1):

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


def get_user_mounts(course_name: str, role):

    mounts = dict()
    mounts[os.path.join(HOME_DIR_ROOT_HOST, '{username}')] = {
        'bind': os.path.join(HOME_DIR_ROOT, '{username}'),
        'mode': 'rw',
    }
    mounts[os.path.join(SHARE_DIR_ROOT_HOST, 'class', course_name)] = {
        'bind': os.path.join(SHARE_DIR_ROOT, 'class', course_name),
        'mode': 'rw',
    }
    mounts[os.path.join(SHARE_DIR_ROOT_HOST, 'nbgrader', 'exchange', course_name)] = {
        'bind': os.path.join(SHARE_DIR_ROOT, 'nbgrader', 'exchange', course_name),
        'mode': 'rw',
    }
    mounts[os.path.join('/exchange', 'sudoers')] = {
        'bind': os.path.join('/etc', 'sudoers'),
        'mode': 'ro',
    }
    if role == McjRoles.INSTRUCTOR.value:
        mounts[os.path.join(SHARE_DIR_ROOT_HOST, course_name, 'opt', 'local', 'sbin')] = {
            'bind': os.path.join('/opt', 'local', 'sbin'),
            'mode': 'rw',
        }
        mounts[os.path.join(SHARE_DIR_ROOT_HOST, course_name, 'opt', 'local', 'bin')] = {
            'bind': os.path.join('/opt', 'local', 'bin'),
            'mode': 'rw',
        }
    else:
        mounts[os.path.join(SHARE_DIR_ROOT_HOST, course_name, 'opt', 'local', 'sbin')] = {
            'bind': os.path.join('/opt', 'local', 'sbin'),
            'mode': 'ro',
        }
        mounts[os.path.join(SHARE_DIR_ROOT_HOST, course_name, 'opt', 'local', 'bin')] = {
            'bind': os.path.join('/opt', 'local', 'bin'),
            'mode': 'ro',
        }
    return mounts


def confirm_share_dir(role, root_uid_num, user_name,
                      uid_num, course):

    course_share_dir_root = os.path.join(SHARE_DIR_ROOT_HOST, 'class')
    share_path = os.path.join(course_share_dir_root, course, 'share')
    submit_root = os.path.join(course_share_dir_root, course, 'submit')
    submit_dir = os.path.join(course_share_dir_root, course, 'submit',
                              user_name)
    class_dir = os.path.join(HOME_DIR_ROOT_HOST, user_name, 'class')

    confirm_dir(submit_root, mode=0o0755, uid=root_uid_num,
                gid=gid_teachers)
    confirm_dir(share_path, mode=0o0775, uid=root_uid_num,
                gid=gid_teachers)

    if role == McjRoles.INSTRUCTOR.value:

        confirm_dir(course_share_dir_root, mode=0o0775, uid=root_uid_num,
                    gid=root_uid_num)
        confirm_dir(course_share_dir_root, mode=0o0775, uid=root_uid_num,
                    gid=gid_teachers)
        confirm_dir(submit_dir, mode=0o0750, uid=uid_num,
                    gid=root_uid_num)
        confirm_dir(os.path.join(SHARE_DIR_ROOT_HOST, course, 'opt', 'local', 'bin'), mode=0o0755, uid=uid_num,
                   gid=-1)
        confirm_dir(os.path.join(SHARE_DIR_ROOT_HOST, course, 'opt', 'local', 'sbin'), mode=0o0755, uid=uid_num,
                   gid=-1)

    else:
        confirm_dir(submit_dir, mode=0o0750, uid=uid_num,
                    gid=gid_teachers)


def get_nrps_token():
    return get_lms_lti_token(IMS_LTI13_NRPS_TOKEN_SCOPE,
                             jupyterhub_fqdn,
                             private_key,
                             token_endpoint,
                             os.environ['LMS_CLIENT_ID'])


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

        user_id = member.get('ext_user_username', member[default_key])

        students.append(
            dict(
                id=user_id,
                first_name=member.get('given_name'),
                last_name=member.get('family_name'),
                email=member.get('email'),
                lms_user_id=member['user_id']))
    return students


def confirm_nbgrader_dir(course_name,
                         role,
                         user_name,
                         root_uid_num,
                         user_uid_num,
                         groupid,
                         students):

    exchange_root_path = os.path.join(SHARE_DIR_ROOT_HOST, 'nbgrader',
                                      'exchange')
    exchange_course_path = os.path.join(exchange_root_path, course_name)
    exchange_inbound_path = os.path.join(exchange_course_path, 'inbound')
    exchange_outbound_path = os.path.join(exchange_course_path, 'outbound')
    exchange_feedback_path = os.path.join(exchange_course_path, 'feedback')

    user_home = os.path.join(HOME_DIR_ROOT_HOST, user_name)
    nbgrader_template_path_base = os.path.join(SHARE_DIR_ROOT_HOST, 'nbgrader',
                                               'templates')
    nbgrader_template_path = os.path.join(nbgrader_template_path_base,
                                          role_config[role]['template_dir_name'])

    confirm_dir(exchange_root_path, mode=0o0755, uid=root_uid_num,
                gid=gid_teachers)

    if role == McjRoles.INSTRUCTOR.value:
        confirm_dir(exchange_course_path, mode=0o0755, uid=user_uid_num,
                    gid=gid_teachers)
        confirm_dir(exchange_inbound_path, mode=0o0733, uid=user_uid_num,
                    gid=gid_students)
        confirm_dir(exchange_outbound_path, mode=0o0755, uid=user_uid_num,
                    gid=gid_students)
        confirm_dir(exchange_feedback_path, mode=0o0711, uid=user_uid_num,
                    gid=gid_students)

        instructor_root_path = os.path.join(user_home, 'nbgrader')
        instructor_log_file = os.path.join(instructor_root_path, 'nbgrader.log')
        course_dir = os.path.join(instructor_root_path, course_name)
        course_autograded_dir = os.path.join(course_dir, 'autograded')
        course_release_dir = os.path.join(course_dir, 'release')
        course_source_dir = os.path.join(course_dir, 'source')
        course_submitted_dir = os.path.join(course_dir, 'submitted')
        course_config_file = os.path.join(course_dir, 'nbgrader_config.py')
        cource_header_file = os.path.join(course_source_dir, 'header.ipynb')
        cource_autotests_yml = os.path.join(course_dir, 'autotests.yml')

        config_template_file = os.path.join(nbgrader_template_path,
                                            'nbgrader_config.py')
        header_template_file = os.path.join(nbgrader_template_path,
                                            'header.ipynb')
        autotests_yml = os.path.join(nbgrader_template_path, 'autotests.yml')

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

        if os.path.exists(course_config_file):
            os.remove(course_config_file)

        with open(course_config_file, mode="w", encoding="utf-8") as f2:
            f2.write(target_lines)

        os.chown(course_config_file, user_uid_num, groupid)
        os.chmod(course_config_file, 0o0644)

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

    if not auth_state:
        return

    lms_username = auth_state[IMS_LTI13_KEY_MEMBER_EXT]['user_username']
    lms_course_shortname = auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['label']
    lms_role = McjRoles.get_user_role(auth_state[IMS_LTI13_KEY_MEMBER_ROLES])
    homedir_host = os.path.join(HOME_DIR_ROOT_HOST, lms_username)
    homedir_container = os.path.join(HOME_DIR_ROOT, lms_username)
    uid_num = int(auth_state['sub']) + 1000
    gid_num = role_config[lms_role]['gid_num']

    ldapconn = ldapClient(ldap_server, ldap_manager_dn, ldap_password)
    search_result = ldapconn.search_user(lms_username, ['uidNumber'])

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
                'homeDirectory': homedir_container,
                'loginShell': role_config[lms_role]['login_shell'],
                'userPassword': get_random_password(12),
                'mail': f'{lms_username}@{email_domain}',
            },
        )
    else:
        ldapconn.update_user(lms_username,
                             {'gidNumber': [(MODIFY_REPLACE, [gid_num])]})

    # ホームディレクトリ作成
    confirm_dir(homedir_host, mode=0o755, uid=uid_num, gid=gid_num)
    if lms_role == McjRoles.INSTRUCTOR.value:
        shutil.copy(os.path.join(skelton_directory, 'README.md'),
                    homedir_host)
        tools_dir = os.path.join(homedir_host, 'teacher_tools')
        if not os.path.isdir(tools_dir):
            shutil.copytree(os.path.join(skelton_directory, 'teacher_tools'),
                            tools_dir)
            set_permission_recursive(tools_dir, uid=uid_num)

    try:
        root_obj = pwd.getpwnam("root")
    except KeyError as e:
        logger.error("Could not find root in passwd.")
        raise e

    root_uid_num = int(root_obj[2])
    # root_gid_num = int(root_obj[3])

    confirm_share_dir(
        lms_role,
        root_uid_num,
        lms_username,
        uid_num,
        lms_course_shortname,
    )

    students = list()
    if get_course_member_method == 'moodle_api':
        students = get_course_students_by_lms_api(
            lms_api_token,
            auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['id'],
            c.LTI13Authenticator.issuer)
    elif c.LTI13Authenticator.username_key == 'email':
        students = get_course_students_by_nrps(
            auth_state[IMS_LTI13_KEY_NRPS]['context_memberships_url'],
            default_key='email')
    else:
        students = get_course_students_by_nrps(
            auth_state[IMS_LTI13_KEY_NRPS]['context_memberships_url'])

    confirm_nbgrader_dir(
        lms_course_shortname, lms_role, lms_username,
        root_uid_num, uid_num, gid_num,
        students)

    spawner.environment = {
        'MOODLECOURSE': lms_course_shortname,
        'COURSEROLE': lms_role,
        'TZ': 'Asia/Tokyo',
        'TEACHER_GID': gid_teachers,
        'STUDENT_GID': gid_students,
        'JUPYTERHUB_FQDN': jupyterhub_fqdn,
        'PATH': f'{homedir_container}/.local/bin:' +
                f'{homedir_container}/bin:/usr/local/bin:/usr/local/sbin:' +
                '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin:' +
                f'{homedir_container}/tools',
        'NB_USER': lms_username,
        'PWD': homedir_container,
        'NB_UID': uid_num,
        'NB_GID': gid_num,
        'HOME': homedir_container,
        'CHOWN_HOME': 'yes',
        'CHOWN_EXTRA_OPTS': '-R',
    }
    if os.getenv('ENABLE_CUSTOM_SETUP'):
        spawner.environment['ENABLE_CUSTOM_SETUP'] = 'yes'

    spawner.extra_container_spec.update({"user": "root",
                                         "workdir": homedir_container})
    spawner.cpu_limit = role_config[lms_role]['cpu_limit']
    spawner.mem_limit = role_config[lms_role]['mem_limit']
    spawner.cpu_guarantee = role_config[lms_role]['cpu_guarantee']
    spawner.mem_guarantee = role_config[lms_role]['mem_guarantee']
    spawner.user.name = lms_username
    spawner.user_id = uid_num
    spawner.group_id = gid_num
    spawner.volumes = get_user_mounts(lms_course_shortname, lms_role)


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
    updated_auth_state['groups'] = [course_name]
    updated_auth_state['name'] = lms_user_name

    if 'roles' not in updated_auth_state:
        updated_auth_state['roles'] = list()

    # デフォルトのuserは使えない？
    updated_auth_state['roles'].append({'name': 'user'})

    role_user_common = {
        'name': 'self',
    #    'scopes': ['users!user=self']
    }
    updated_auth_state['roles'].append(role_user_common)
    if McjRoles.is_instructor(authentication['auth_state'][IMS_LTI13_KEY_MEMBER_ROLES]):
        role_course_admin = {
            'name': f'instructor-{course_name}',
            'scopes': [
                'admin-ui',
                f'list:users!group={course_name}',
                f'admin:servers!group={course_name}',
                f"access:servers!group={course_name}",
            ]}
        role_instructor_common = {
            'name': 'instructor',
            'scopes': ['access:services', "access:services!service=mcjapi", "access:services!service=announcement"]
        }
        role_jupyterhub_admin = {'name': 'admin'}
        updated_auth_state['roles'].append(role_instructor_common)
        updated_auth_state['roles'].append(role_course_admin)

    if jupyterhub_admin_users is not None and lms_user_name in jupyterhub_admin_users:
        updated_auth_state['roles'].append(role_jupyterhub_admin)

    return updated_auth_state


c.SwarmSpawner.auth_state_hook = auth_state_hook
c.Authenticator.post_auth_hook = post_auth_hook
