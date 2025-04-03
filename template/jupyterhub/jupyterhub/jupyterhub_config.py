import base64
import copy
from enum import Enum
import hashlib
import logging
import os
import pwd
import secrets
import shutil
import string
import sys
import time
import jwt
import requests
import urllib
import yaml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPNoSuchObjectResult

from lms_web_service import get_course_students_by_lms_api
from mcj_spawner import SysUserSwarmSpawner


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

local_ldap_password = os.environ['LDAP_PASSWORD']
local_ldap_server = 'openldap:1389'
local_ldap_base_dn = 'ou=People,dc=jupyterhub,dc=server,dc=sample,dc=jp'
local_ldap_manager_dn = f'cn={os.getenv("LDAP_USER", "Manager")},dc=jupyterhub,dc=server,dc=sample,dc=jp'

database_dbhost = 'mariadb'
database_dbname = 'jupyterhub'
database_username = os.getenv('DB_USER', 'jupyter')
database_password = os.environ['DB_PASSWORD']

get_course_member_method = os.getenv('LTI_METHOD')
lms_api_token = os.getenv('LMS_API_TOKEN')

home_directory_root = os.environ['HOME_DIR_ROOT']
share_directory_root = os.environ['SHARE_DIR_ROOT']
skelton_directory = f'{home_directory_root}/skelton'
email_domain = os.getenv('EMAIL_DOMAIN', 'example.com')

with open('/etc/jupyterhub/jupyterhub_params.yaml', 'r', encoding="utf-8") as yml:
    config = yaml.safe_load(yml)

c = get_config() # noqa

c.JupyterHub.base_url = os.getenv('JUPYTERHUB_BASE_URL', '/')

# cookie max-age (days) is 6 hours
c.JupyterHub.cookie_max_age_days = config.get(
    'cookie_max_age_days', DEFUALT_COOKIE_MAX_AGE_DAYS)

if config.get('cull_server') is not None:
    cull_server_idle_timeout = config['cull_server'].get(
        'cull_server_timeout', DEFUALT_IDLE_TIMEOUT)
    cull_server_every = config['cull_server'].get(
        'cull_server_every', DEFUALT_CULL_EVERY)
    cull_server_max_age = config['cull_server'].get(
        'cull_server_max_age', DEFUALT_SERVER_MAX_AGE)
else:
    cull_server_idle_timeout = DEFUALT_IDLE_TIMEOUT
    cull_server_every = DEFUALT_CULL_EVERY
    cull_server_max_age = DEFUALT_SERVER_MAX_AGE

if cull_server_idle_timeout > 0:
    c.JupyterHub.load_roles = [
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
    ]
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

c.JupyterHub.services.append({
    'name': 'mcjapi',
    'url': f'http://jupyterhub:10101/{c.JupyterHub.base_url}',
    'command': ['python3', '/etc/jupyterhub/handler.py'],
    'admin': True,
})

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
# Maximum number of concurrent servers that can be active at a time.
c.JupyterHub.active_server_limit = 400
# Duration (in seconds) to determine the number of active users.
c.JupyterHub.active_user_window = 600
# Resolution (in seconds) for updating activity
c.JupyterHub.activity_resolution = 30
# Maximum number of concurrent named servers that can be created by a user at a time.
c.JupyterHub.named_server_limit_per_user = 1
# Maximum number of concurrent users that can be spawning at a time.
c.JupyterHub.concurrent_spawn_limit = 100
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
# c.Authenticator.admin_users = jupyterhub_admin_users
c.Authenticator.enable_auth_state = True
c.Authenticator.manage_groups = True

# -- configurations for lti1.3 --
# Define issuer identifier of the LMS platform
c.LTI13Authenticator.issuer = os.getenv('LMS_PLATFORM_ID')
# Add the LTI 1.3 configuration options
c.LTI13Authenticator.authorize_url = f'{c.LTI13Authenticator.issuer}/mod/lti/auth.php'
# The platform's JWKS endpoint url providing public key sets used to verify the ID token
c.LTI13Authenticator.jwks_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/certs.php'
# The platform's endpoint url for creating access token
# c.LTI13Authenticator.token_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/token.php'
token_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/token.php'

# The external tool's client id as represented within the platform (LMS)
c.LTI13Authenticator.client_id = os.getenv('LMS_CLIENT_ID')
# default 'email'
c.LTI13Authenticator.username_key = os.getenv('LTI_USERNAME_KEY', 'email')

# Use UniversitySwarmSpawner.
# c.JupyterHub.spawner_class = 'dockerspawner.SysUserSwarmSpawner'
c.JupyterHub.spawner_class = SysUserSwarmSpawner

# -- configurations for Spawner --
# idle time for HTTP timeout.
c.Spawner.http_timeout = 300
c.Spawner.default_url = os.getenv('DEFAULT_URL', "/lab")

# Image of Noetbook
c.SysUserSwarmSpawner.image = os.getenv('NOTEBOOK_IMAGE')

# this is the network name for jupyterhub in docker-compose.yml
# with a leading 'swarm_' that docker-compose adds
c.SysUserSwarmSpawner.network_name = os.getenv('DOCKER_NETWORK_NAME')
c.SysUserSwarmSpawner.extra_host_config = {
    'network_mode': os.getenv('DOCKER_NETWORK_NAME')}
c.SysUserSwarmSpawner.extra_placement_spec = {
    'constraints': [f'node.role == {os.getenv("NB_NODE_ROLE", "manager")}']}

c.SysUserSwarmSpawner.debug = True

# launch timeout
c.SysUserSwarmSpawner.start_timeout = 300

c.SysUserSwarmSpawner.ldap_server = local_ldap_server
c.SysUserSwarmSpawner.ldap_password = local_ldap_password
c.SysUserSwarmSpawner.ldap_base_dn = local_ldap_base_dn
c.SysUserSwarmSpawner.ldap_manager_dn = local_ldap_manager_dn

nrps_token = None


class Role(Enum):
    INSTRUCTOR = 'Instructor'
    LEARNER = 'Learner'

    @classmethod
    def get_values(cls) -> list:
        return [d.value for d in cls]


role_config = {
    Role.INSTRUCTOR.value: {
        'cpu_limit': config['resource']['groups']['teacher']['cpu_limit'],
        'mem_limit': config['resource']['groups']['teacher']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['teacher']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['teacher']['mem_guarantee'],
        'gid_num': gid_teachers,
        'login_shell': '/bin/bash',
        'template_dir_name': 'teachers',
    },
    Role.LEARNER.value: {
        'cpu_limit': config['resource']['groups']['student']['cpu_limit'],
        'mem_limit': config['resource']['groups']['student']['mem_limit'],
        'cpu_guarantee': config['resource']['groups']['student']['cpu_guarantee'],
        'mem_guarantee': config['resource']['groups']['student']['mem_guarantee'],
        'gid_num': gid_students,
        'login_shell': '/sbin/nologin',
        'template_dir_name': 'students',
    },
}


class YHException(Exception):
    def __init__(self, arg=''):
        self.arg = arg


class InvalidUserInfoException(YHException):
    def __str__(self):
        return (
            f'ERROR: organization_user [{self.arg}]'
        )


class CreateDirectoryException(YHException):
    def __str__(self):
        return (
            f'ERROR: Could not create directory: [{self.arg}]'
        )


class FailedAuthStateHookException(YHException):
    def __str__(self):
        return (
            'ERROR: Failed to auth_state_hook. See the log to get detail.'
        )


def change_owner(homePath, uid, gid):
    for root, dirs, files in os.walk(homePath):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
    os.chown(homePath, uid, gid)


def search_local_ldap(username, attributes: list = None):

    try:
        server = Server(c.SysUserSwarmSpawner.ldap_server, get_info=ALL)
        conn = Connection(
            server,
            c.SysUserSwarmSpawner.ldap_manager_dn,
            password=c.SysUserSwarmSpawner.ldap_password,
            read_only=True,
            raise_exceptions=True,
        )
        conn.bind()
        conn.search(
            f'uid={username},{c.SysUserSwarmSpawner.ldap_base_dn}',
            '(objectClass=*)',
            attributes=attributes,
        )

        return copy.deepcopy(conn.entries)

    except LDAPNoSuchObjectResult:
        return
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


def add_local_ldap(dn, object_class=None, attributes=None, controls=None):

    server = Server(c.SysUserSwarmSpawner.ldap_server, get_info=ALL)
    conn = Connection(
        server,
        c.SysUserSwarmSpawner.ldap_manager_dn,
        password=c.SysUserSwarmSpawner.ldap_password,
        read_only=False,
        raise_exceptions=True,
    )
    conn.bind()
    conn.add(
        dn,
        object_class,
        attributes,
        controls,
    )

    try:
        conn.unbind()
    except Exception:
        pass


def update_ldap(user_name, gid_num):

    server = Server(c.SysUserSwarmSpawner.ldap_server, get_info=ALL)
    conn = Connection(
        server,
        c.SysUserSwarmSpawner.ldap_manager_dn,
        password=c.SysUserSwarmSpawner.ldap_password,
        read_only=False,
        raise_exceptions=True,
    )
    conn.bind()
    conn.modify(
        f'uid={user_name},{c.SysUserSwarmSpawner.ldap_base_dn}',
        {'gidNumber': [(MODIFY_REPLACE, [gid_num])]}
    )

    try:
        conn.unbind()
    except Exception:
        pass


def create_common_share_path(ext_course_path,
                             local_course_path,
                             role,
                             root_uid_num,
                             user_name,
                             uid_num):

    ext_share_path = f'{ext_course_path}/share'
    ext_submit_root = f'{ext_course_path}/submit'
    ext_submit_dir = f'{ext_course_path}/submit/{user_name}'
    mount_volumes = list()

    create_dir(ext_submit_root, mode=0o0755, uid=root_uid_num,
               gid=gid_teachers)
    create_dir(ext_share_path, mode=0o0775, uid=root_uid_num,
               gid=gid_teachers)

    if role == Role.INSTRUCTOR.value:
        create_dir(ext_submit_dir, mode=0o0750, uid=uid_num,
                   gid=root_uid_num)
    else:
        create_dir(ext_submit_dir, mode=0o0750, uid=uid_num,
                   gid=gid_teachers)

    mount_volumes.append(
        {'type': 'bind',
         'source': '/exchange/sudoers',
         'target': '/etc/sudoers',
         'ReadOnly': True})

    return mount_volumes


def get_course_students_by_nrps(url, default_key='user_id'):

    global nrps_token
    if nrps_token is None:
        nrps_token = get_nrps_token()

    headers = {'Authorization': f'Bearer {nrps_token}'}
    response = requests.get(
        url,
        headers=headers,
    )
    if response.status_code == 401:

        logger.info('LMS access token expired')
        nrps_token = get_nrps_token()
        headers = {'Authorization': f'Bearer {nrps_token}'}
        response = requests.get(
            url,
            headers=headers,
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


def create_dir(dir, mode=0o700, uid=-1, gid=-1):

    os.makedirs(dir, exist_ok=True)
    os.chmod(dir, mode=mode)
    os.chown(dir, uid, gid)


def create_nbgrader_path(course_short_name,
                         role,
                         user_name,
                         root_uid_num,
                         user_uid_num,
                         groupid,
                         auth_state):

    exchange_root_path = f'{share_directory_root}/nbgrader/exchange'
    exchange_course_path = f'{exchange_root_path}/{course_short_name}'
    exchange_inbound_path = f'{exchange_course_path}/inbound'
    exchange_outbound_path = f'{exchange_course_path}/outbound'
    exchange_feedback_path = f'{exchange_course_path}/feedback'

    user_home = f'{home_directory_root}/{user_name}'
    nbgrader_template_path_base = f'{share_directory_root}/nbgrader/templates'
    nbgrader_template_path = f"{nbgrader_template_path_base}/{role_config[role]['template_dir_name']}"

    create_dir(exchange_root_path, mode=0o0755, uid=root_uid_num,
               gid=gid_teachers)

    if role == Role.INSTRUCTOR.value:
        create_dir(exchange_course_path, mode=0o0755, uid=user_uid_num,
                   gid=gid_teachers)
        create_dir(exchange_inbound_path, mode=0o0733, uid=user_uid_num,
                   gid=gid_students)
        create_dir(exchange_outbound_path, mode=0o0755, uid=user_uid_num,
                   gid=gid_students)
        create_dir(exchange_feedback_path, mode=0o0711, uid=user_uid_num,
                   gid=gid_students)

        instructor_root_path = user_home + '/nbgrader'
        instructor_log_file = instructor_root_path + '/nbgrader.log'
        course_path = instructor_root_path + '/' + course_short_name
        course_autograded_path = course_path + '/autograded'
        course_release_path = course_path + '/release'
        course_source_path = course_path + '/source'
        course_submitted_path = course_path + '/submitted'
        course_config_file = course_path + '/nbgrader_config.py'
        cource_header_file = course_source_path + '/header.ipynb'
        cource_autotests_yml = course_path + '/autotests.yml'

        config_template_file = f'{nbgrader_template_path}/nbgrader_config.py'
        header_template_file = f'{nbgrader_template_path}/header.ipynb'
        autotests_yml = f'{nbgrader_template_path}/autotests.yml'

        create_dir(instructor_root_path, uid=user_uid_num,
                   gid=gid_teachers, mode=0o0755)
        create_dir(course_path, uid=user_uid_num, gid=gid_teachers, mode=0o0755)
        create_dir(course_autograded_path, mode=0o0755, uid=user_uid_num,
                   gid=groupid)
        create_dir(course_release_path, mode=0o0755, uid=user_uid_num,
                   gid=groupid)
        create_dir(course_source_path, mode=0o2755, uid=user_uid_num,
                   gid=groupid)
        create_dir(course_submitted_path, mode=0o0755, uid=user_uid_num,
                   gid=groupid)

        if os.path.exists(course_path):
            if os.path.exists(course_config_file):
                os.remove(course_config_file)

            with open(config_template_file, encoding="utf-8") as f1:
                target_lines = f1.read()

            if get_course_member_method == 'moodle_api':
                studentlist = get_course_students_by_lms_api(
                    lms_api_token,
                    auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['id'],
                    c.LTI13Authenticator.issuer)
            elif c.LTI13Authenticator.username_key == 'email':
                studentlist = get_course_students_by_nrps(
                    auth_state[IMS_LTI13_KEY_NRPS]['context_memberships_url'],
                    default_key='email')
            else:
                studentlist = get_course_students_by_nrps(
                    auth_state[IMS_LTI13_KEY_NRPS]['context_memberships_url'])

            target_lines = target_lines.replace(
                'NBG_STUDENTS = []', f"NBG_STUDENTS = {str(studentlist)}")

            with open(course_config_file, mode="w", encoding="utf-8") as f2:
                f2.write(target_lines)

            os.chown(course_config_file, user_uid_num, groupid)
            os.chmod(course_config_file, 0o0644)

        if os.path.exists(course_source_path) \
                and not os.path.exists(cource_header_file):

            shutil.copyfile(header_template_file, cource_header_file)
            os.chown(cource_header_file, user_uid_num, groupid)
            os.chmod(cource_header_file, 0o0644)

        if os.path.exists(course_source_path) \
                and not os.path.exists(cource_autotests_yml):

            shutil.copyfile(autotests_yml, cource_autotests_yml)
            os.chown(cource_autotests_yml, user_uid_num, groupid)
            os.chmod(cource_autotests_yml, 0o0644)

        if os.path.exists(instructor_log_file):
            fp = open(instructor_log_file, 'r+', encoding="utf-8")
            fp.truncate(0)
            fp.close()
            os.chown(instructor_log_file, user_uid_num, groupid)
            os.chmod(instructor_log_file, 0o0644)


def create_userdata(spawner,
                    moodle_username,
                    course_shortname,
                    moodle_role,
                    auth_state):

    ext_root_path = f'{share_directory_root}/class'
    ext_course_path = f'{ext_root_path}/{course_shortname}'
    user_home_path = f'{home_directory_root}/{moodle_username}'

    mount_volumes = []
    change_flag = False

    if not isinstance(spawner.extra_container_spec, dict) \
            or 'mounts' not in spawner.extra_container_spec:
        change_flag = True
    elif not spawner.extra_container_spec['mounts']:
        change_flag = True
    elif course_shortname not in str(spawner.extra_container_spec['mounts']) \
            or moodle_username not in str(spawner.extra_container_spec['mounts']):
        change_flag = True
    else:
        for item in spawner.extra_container_spec['mounts']:
            if course_shortname in str(item['source']) \
                    and (course_shortname not in str(item['target'])
                         or moodle_username not in str(item['target'])):
                change_flag = True
            elif not os.path.exists(item['source']):
                change_flag = True

    if change_flag:
        try:
            root_obj = pwd.getpwnam("root")
        except KeyError as e:
            logger.error("Could not find root in passwd.")
            raise e

        root_uid_num = int(root_obj[2])
        root_gid_num = int(root_obj[3])

        res = search_local_ldap(moodle_username, ['uidNumber', 'gidNumber'])
        uid_num = res[0]['uidNumber'].value if res is not None else -1
        gid_num = res[0]['gidNumber'].value if res is not None else -1

        if uid_num <= 0:
            uid_num = root_uid_num
            gid_num = root_gid_num

        if os.path.islink(user_home_path + '/class'):
            os.unlink(user_home_path + '/class')

        os.symlink('/jupytershare/class', user_home_path + '/class')
        mount_volumes = [
            {'type': 'bind',
             'source': user_home_path,
             'target': f'/home/{moodle_username}'}]

        if moodle_role == Role.INSTRUCTOR.value:

            if not os.path.exists(ext_root_path):
                create_dir(ext_root_path, mode=0o0775, uid=root_uid_num,
                           gid=root_uid_num)

            create_dir(ext_course_path, mode=0o0775, uid=root_uid_num,
                       gid=gid_teachers)

            if not os.path.exists(ext_course_path):
                raise CreateDirectoryException(ext_course_path)

        mount_volumes.append(
            {'type': 'bind',
             'source': share_directory_root + '/class/' + course_shortname,
             'target': '/jupytershare/class/' + course_shortname})

        mount_volumes.append(
            {'type': 'bind',
             'source': share_directory_root + '/nbgrader/exchange/' + course_shortname,
             'target': '/jupytershare/nbgrader/exchange/' + course_shortname})

        local_course_path_in_container = f'/home/{moodle_username}/class/{course_shortname}'
        common_volumes = create_common_share_path(
            ext_course_path,
            local_course_path_in_container,
            moodle_role,
            root_uid_num,
            moodle_username,
            uid_num,
        )

        for item in common_volumes:
            if item not in mount_volumes:
                mount_volumes.append(item)

        create_nbgrader_path(
            course_shortname, moodle_role, moodle_username,
            root_uid_num, uid_num, gid_num,
            auth_state)

    return mount_volumes


def get_random_password(size=12):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    chars += '=+-[]!$():./*'

    random_pass = ''.join(secrets.choice(chars) for _ in range(size))
    salt = os.urandom(4)
    md = hashlib.sha1(random_pass.encode('utf-8'))
    md.update(salt)
    digest_pass = base64.b64encode(
        '{}{}'.format(md.digest(), salt).encode('utf-8'))
    digest_pass = digest_pass.strip()
    random_pass = '{SSHA}' + digest_pass.decode('utf-8')
    return random_pass


def get_user_role(auth_state):

    rolelist = auth_state[IMS_LTI13_KEY_MEMBER_ROLES]
    instructor_flag = False
    learner_flag = False
    role = ''

    # Get user's role.
    for rolename in rolelist:
        param_type, role = rolename.split('#')
        if not param_type == IMS_LTI13_KEY_MEMBERSHIP:
            continue
        if role == Role.INSTRUCTOR.value:
            instructor_flag = True
        elif role == Role.LEARNER.value:
            learner_flag = True

    if not learner_flag and instructor_flag:
        role = Role.INSTRUCTOR.value
    else:
        role = Role.LEARNER.value

    return role


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


def create_home_hook(spawner, auth_state):

    if not auth_state:
        return

    lms_username = auth_state[IMS_LTI13_KEY_MEMBER_EXT]['user_username']
    lms_course_shortname = auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['label']
    lms_role = get_user_role(auth_state)
    user_home = f'{home_directory_root}/{lms_username}'
    uid_num = int(auth_state['sub']) + 1000
    search_result = search_local_ldap(lms_username, ['uidNumber'])

    if search_result is None:
        add_local_ldap(
            f'uid={lms_username},{c.SysUserSwarmSpawner.ldap_base_dn}',
            ['posixAccount', 'inetOrgPerson'],
            {
                'uid': lms_username,
                'cn': lms_username,
                'sn': lms_username,
                'uidNumber': uid_num,
                'gidNumber': role_config[lms_role]['gid_num'],
                'homeDirectory': f'/home/{lms_username}',
                'loginShell': role_config[lms_role]['login_shell'],
                'userPassword': get_random_password(12),
                'mail': f'{lms_username}@{email_domain}',
            },
        )
    else:
        update_ldap(lms_username, role_config[lms_role]['gid_num'])

    # ホームディレクトリ作成
    create_dir(user_home, mode=0o755, uid=uid_num, gid=role_config[lms_role]['gid_num'])
    if lms_role == Role.INSTRUCTOR.value:
        shutil.copy(os.path.join(skelton_directory, 'README.md'),
                    user_home)
        tools_dir = os.path.join(user_home, 'teacher_tools')
        if not os.path.isdir(tools_dir):
            shutil.copytree(os.path.join(skelton_directory, 'teacher_tools'),
                            tools_dir)
            set_permission_recursive(tools_dir, uid=uid_num)

    spawner.environment = {
        'MOODLECOURSE': auth_state[IMS_LTI13_KEY_MEMBER_CONTEXT]['label'],
        'COURSEROLE': lms_role,
        'TZ': 'Asia/Tokyo',
        'PWD': user_home,
        'TEACHER_GID': gid_teachers,
        'STUDENT_GID': gid_students,
        'JUPYTERHUB_FQDN': jupyterhub_fqdn,
        'PATH': f'{user_home}/.local/bin:' +
                f'{user_home}/bin:/usr/local/bin:/usr/local/sbin:' +
                '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin:' +
                f'/home/{lms_username}/tools',
    }

    spawner.cpu_limit = role_config[lms_role]['cpu_limit']
    spawner.mem_limit = role_config[lms_role]['mem_limit']
    spawner.cpu_guarantee = role_config[lms_role]['cpu_guarantee']
    spawner.mem_guarantee = role_config[lms_role]['mem_guarantee']

    # Create userdata for subject.
    mount_volumes = create_userdata(
        spawner, lms_username, lms_course_shortname, lms_role, auth_state)

    if isinstance(mount_volumes, list) and len(mount_volumes) != 0:
        spawner.extra_container_spec['mounts'] = mount_volumes
        spawner.extra_container_spec['user'] = '0'

    spawner.login_user_name = lms_username
    spawner.user_id = uid_num
    spawner.group_id = role_config[lms_role]['gid_num']
    spawner.homedir = f'/home/{lms_username}'


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
    updated_auth_state['groups'] = [get_user_role(authentication['auth_state'])]
    updated_auth_state['name'] = lms_user_name
    return updated_auth_state


def get_or_generate_nrps_keypair():

    # Import key when already exists or Create key when not exists
    if os.path.isfile(f'{os.path.dirname(__file__)}/public_key_nrps.pem') and \
       os.path.isfile(f'{os.path.dirname(__file__)}/private_key_nrps.pem'):
        with open(f'{os.path.dirname(__file__)}/private_key_nrps.pem', "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
        with open(f'{os.path.dirname(__file__)}/public_key_nrps.pem', "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read(),
            )

    else:
        # 鍵の生成
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # 公開鍵
        public_key = private_key.public_key()

        # 鍵をファイル出力する
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(f"{os.path.dirname(__file__)}/public_key_nrps.pem", "w+b") as f:
            f.write(public_key_pem)

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(f"{os.path.dirname(__file__)}/private_key_nrps.pem", "w+b") as f:
            f.write(private_key_pem)

        os.chmod(f"{os.path.dirname(__file__)}/private_key_nrps.pem", 0o0400)

    return private_key, public_key


def get_nrps_jwt():

    private_key, public_key = get_or_generate_nrps_keypair()
    current_unix_time = int(time.time())
    token_value = {
        "iss": f"https://{jupyterhub_fqdn}",
        "iat": current_unix_time,
        "exp": current_unix_time + 60 * 60 * 24 * 100,
        "aud": token_endpoint,
        "sub": c.LTI13Authenticator.client_id
    }

    return jwt.encode(
        token_value, private_key, algorithm="RS256")


def get_nrps_token():
    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': IMS_LTI13_NRPS_ASSERT_TYPE,
        'client_assertion': encoded_jwt,
        'scope': IMS_LTI13_NRPS_TOKEN_SCOPE,
    }
    data = urllib.parse.urlencode(data)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    response = requests.post(
        token_endpoint,
        headers=headers,
        data=data,
        timeout=300
    )

    if 200 != response.status_code:
        logger.error(response.text)
        raise YHException("Failed to get nrps token from LMS. Public key in outer tool settings in LMS may be wrong")

    return response.json()['access_token']


encoded_jwt = get_nrps_jwt()
c.SysUserSwarmSpawner.auth_state_hook = create_home_hook
c.Authenticator.post_auth_hook = post_auth_hook
