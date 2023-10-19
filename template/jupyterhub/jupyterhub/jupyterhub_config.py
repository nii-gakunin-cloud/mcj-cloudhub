import base64
import copy
import hashlib
import logging
import os
import pwd
import secrets
import shutil
import string
import sys
import grp

from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPNoSuchObjectResult
import pymysql.cursors

LOG_FORMAT = '[%(levelname)s %(asctime)s %(module)s %(funcName)s:%(lineno)d] %(message)s'
DIR_NAME_TEMPLATE_TEACHER = 'teachers'
DIR_NAME_TEMPLATE_STUDENT = 'students'
CONTEXTLEVEL_COURSE = 50
ROLE_INSTRUCTOR = 'Instructor'
ROLE_LEARNER = 'Learner'

# logger setting
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(log_formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

c = get_config() # noqa

# The proxy is in another container
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = 'http://proxy:8001'

# The Hub should listen on all interfaces,
# so user servers can connect
c.JupyterHub.hub_ip = '0.0.0.0'
# this is the name of the 'service' in docker-compose.yml
c.JupyterHub.hub_connect_ip = 'hub'
# Initialize processing timeout for spawners.
c.JupyterHub.init_spawners_timeout = 60
# cookie max-age (days) is 90 minutes
c.JupyterHub.cookie_max_age_days = 0.0625
c.Authenticator.refresh_pre_spawn = True
c.Authenticator.auth_refresh_age = 300

# Shutdown active kernels (notebooks) when user logged out.
c.JupyterHub.shutdown_on_logout = True
# Whether to shutdown single-user servers when the Hub shuts down.
c.JupyterHub.cleanup_servers = True

# Set idle time for HTTP timeout.
c.Spawner.http_timeout = 300

# debug-logging for testing
c.JupyterHub.log_level = logging.DEBUG
# c.JupyterHub.log_level = logging.ERROR

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
# 好き勝手にPullされるのは困る気がする デフォルトNGで、ノートブックで設定可能にする？
# c.DockerSpawner.pull_policy = 'ifnotpresent'

EXPECTED_ROLES = (ROLE_INSTRUCTOR, ROLE_LEARNER)

jupyterhub_admin_users = {{jupyterhub_admin_users}}
jupyterhub_groupid_teachers = {{groupid_teachers}}
jupyterhub_groupid_students = {{groupid_students}}

local_ldap_server = '{{ldap_server}}'
local_ldap_password = '{{ldap_password}}'
local_ldap_base_dn = '{{ldap_base_dn}}'
local_ldap_manager_dn = '{{ldap_manager_dn}}'

database_dbhost = '{{jh_db_host}}'
database_username = '{{jh_db_user}}'
database_password = '{{jh_db_password}}'
database_dbname = '{{jh_db_name}}'

moodle_database_dbhost = '{{moodle_db_host}}'
moodle_database_username = '{{moodle_db_user}}'
moodle_database_password = '{{moodle_db_password}}'
moodle_database_dbname = '{{moodle_db_name}}'

home_directory_root = '{{home_directory_root}}'
share_directory_root = '{{share_directory_root}}'

notebook_template_root = '{{notebook_dir}}'

skelton_directory = f'{home_directory_root}/skelton'

email_domain = '{{email_domain}}'
mem_guarantee = '{{mem_guarantee}}'
teacher_mem_limit = '{{teacher_mem_limit}}'
student_mem_limit = '{{student_mem_limit}}'
cpu_guarantee = float({{cpu_guarantee}})
cpu_limit = float({{cpu_limit}})

notebook_image = '{{singleuser_image}}'
swarm_network = '{{swarm_network}}'

logger.info(jupyterhub_admin_users)
logger.info(jupyterhub_groupid_teachers)
logger.info(jupyterhub_groupid_students)
logger.info(local_ldap_server)
logger.info(local_ldap_password)
logger.info(local_ldap_base_dn)
logger.info(local_ldap_manager_dn)
logger.info(database_dbhost)
logger.info(database_username)
logger.info(database_password)
logger.info(database_dbname)
logger.info(moodle_database_dbhost)
logger.info(moodle_database_username)
logger.info(moodle_database_password)
logger.info(moodle_database_dbname)
logger.info(home_directory_root)
logger.info(share_directory_root)
logger.info(skelton_directory)
logger.info(email_domain)

# -- Set LTI authenticator --
# lti1.3
c.JupyterHub.authenticator_class = "ltiauthenticator.lti13.auth.LTI13Authenticator"

# -- configurations for lti1.3 --
# Define issuer identifier of the LMS platform
c.LTI13Authenticator.issuer = '{{moodle_platform_id}}'
# Add the LTI 1.3 configuration options
c.LTI13Authenticator.authorize_url = f'{c.LTI13Authenticator.issuer}/mod/lti/auth.php'
# The platform's JWKS endpoint url providing public key sets used to verify the ID token
c.LTI13Authenticator.jwks_endpoint = f'{c.LTI13Authenticator.issuer}/mod/lti/certs.php'
# The external tool's client id as represented within the platform (LMS)
c.LTI13Authenticator.client_id = '{{moodle_cliend_id}}'
# default 'email'
c.LTI13Authenticator.username_key = 'unspecify'
# additional config for yamaguchi-hub
c.LTI13Authenticator.username_keys = ['https://purl.imsglobal.org/spec/lti/claim/ext', 'user_username']

# Set administrator users.
c.Authenticator.admin_users = jupyterhub_admin_users

if 'JUPYTERHUB_CRYPT_KEY' not in os.environ:
    logger.warn(
        'Need JUPYTERHUB_CRYPT_KEY env for persistent auth_state.'
        '    export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)'
    )
    c.CryptKeeper.keys = [os.urandom(32)]

# Use auth state parameters.
c.Authenticator.enable_auth_state = True

c.JupyterHub.db_kwargs = {'pool_recycle': 300}

# url for the database. e.g. `sqlite:///jupyterhub.sqlite`
#  Default: 'sqlite:///jupyterhub.sqlite'
# c.JupyterHub.db_url = 'sqlite:///jupyterhub.sqlite'
# Use MySQL (mariadb)
c.JupyterHub.db_url = 'mysql+mysqlconnector://{}:{}@{}/{}{}'.format(
    database_username,
    database_password,
    database_dbhost,
    database_dbname,
    '')

# Use UniversitySwarmSpawner.
c.JupyterHub.spawner_class = 'dockerspawner.UniversitySwarmSpawner'
# Set home directory path.
c.UniversitySwarmSpawner.host_homedir_format_string = \
    home_directory_root + '/{username}'

# Image of Noetbook
c.UniversitySwarmSpawner.image = notebook_image

# this is the network name for jupyterhub in docker-compose.yml
# with a leading 'swarm_' that docker-compose adds
c.UniversitySwarmSpawner.network_name = 'swarm_jupyterhub-net'
c.UniversitySwarmSpawner.extra_host_config = {
    'network_mode': 'swarm_jupyterhub-net'}
c.UniversitySwarmSpawner.extra_placement_spec = {
    'constraints': ['node.role == worker']}

c.UniversitySwarmSpawner.debug = True

# increase launch timeout because initial image pulls can take a while
c.UniversitySwarmSpawner.start_timeout = 300

c.UniversitySwarmSpawner.ldap_server = local_ldap_server
c.UniversitySwarmSpawner.ldap_password = local_ldap_password
c.UniversitySwarmSpawner.ldap_base_dn = local_ldap_base_dn
c.UniversitySwarmSpawner.ldap_manager_dn = local_ldap_manager_dn

c.UniversitySwarmSpawner.image_homedir_format_string = \
    home_directory_root + '/{username}'

c.DockerSpawner.remove_containers = True
c.DockerSpawner.remove = True

c.Spawner.escape = 'legacy'

# Start jupyterlab.
# Start jupyter notebook for single user.
c.UniversitySwarmSpawner.cmd = ['/usr/local/bin/start-singleuser.sh']
c.UniversitySwarmSpawner.args = ['--allow-root']

# Resource allocation restriction per user (for production server).
c.UniversitySwarmSpawner.cpu_guarantee = cpu_guarantee
c.UniversitySwarmSpawner.cpu_limit = cpu_limit
c.UniversitySwarmSpawner.mem_guarantee = mem_guarantee
c.UniversitySwarmSpawner.mem_limit = student_mem_limit
c.Authenticator.enable_auth_state = True


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
            'ERROR: Failed to auth_state_hook. See the log to get detail'
        )


def set_user_environment_variables(spawner, auth_state, username):

    if not auth_state:
        return

    if get_ldap_userid(username) <= 0:
        return

    if not spawner.user.name == username:
        return

    role = get_user_role(auth_state)
    user_home = f"{home_directory_root}/{username}"
    spawner.environment = {
        'MOODLECOURSE': auth_state['https://purl.imsglobal.org/spec/lti/claim/context']['label'],
        'MPLCONFIGDIR': user_home + '/.cache/matplotlib',
        'COURSEROLE': role,
        'TZ': 'Asia/Tokyo',
        'GRANT_SUDO': 'yes',
        'HOME': user_home,
        'PWD': user_home,
        'PATH': f'{user_home}/.local/bin:' +
                f'{user_home}/bin:/usr/local/bin:/usr/local/sbin:' +
                '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin'}

    if ROLE_INSTRUCTOR == role:
        c.UniversitySwarmSpawner.mem_limit = teacher_mem_limit
    else:
        c.UniversitySwarmSpawner.mem_limit = student_mem_limit


def change_owner(homePath, uid, gid):
    for root, dirs, files in os.walk(homePath):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
    os.chown(homePath, uid, gid)


def search_local_ldap(username, attributes: list):

    try:
        server = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)

        conn = Connection(
            server,
            c.UniversitySwarmSpawner.ldap_manager_dn,
            password=c.UniversitySwarmSpawner.ldap_password,
            read_only=False,
            raise_exceptions=True)
        logger.debug('Make connection to local ldap server.')
        conn.bind()
        logger.debug('Successfully bind to local ldap server.')

        conn.search(
            f'uid={username},{c.UniversitySwarmSpawner.ldap_base_dn}',
            '(objectClass=*)',
            attributes=attributes)

        return copy.deepcopy(conn.entries)

    except LDAPNoSuchObjectResult:
        logger.debug(f'No such user :{username}')
        return
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


def add_local_ldap(dn, object_class=None, attributes=None, controls=None):

    server = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)
    conn = Connection(
        server,
        c.UniversitySwarmSpawner.ldap_manager_dn,
        password=c.UniversitySwarmSpawner.ldap_password,
        read_only=False,
        raise_exceptions=True)
    logger.debug('Make connection to local ldap server.')
    conn.bind()
    logger.debug('Successfully bind to local ldap server.')
    conn.add(dn, object_class, attributes, controls)

    try:
        conn.unbind()
    except Exception:
        pass


def get_ldap_userid(username):

    logger.debug('Hello, get_ldap_userid.')
    attr = 'uidNumber'
    uid_number = -1

    search_result = search_local_ldap(username, [attr])

    if search_result is None:
        return uid_number

    # The user is exists in local ldap server.
    logger.debug(f'User {username} exists in local ldap.')
    logger.debug(str(search_result[0]))
    uid_number = search_result[0][attr].value

    logger.debug('Finish, get_ldap_userid.')
    return uid_number


def get_ldap_groupid(username):
    logger.debug("Hello, get_ldap_groupid.")

    attr = 'gidNumber'
    gid_number = -1

    search_result = search_local_ldap(username, [attr])

    if search_result is None:
        return gid_number

    logger.debug(f'User ({username}) exists in local ldap.')
    logger.debug(str(search_result[0]))
    gid_number = search_result[0][attr].value

    logger.debug('Finish, get_ldap_groupid.')
    return gid_number


def create_common_share_path(ext_course_path, local_course_path, role, rootid, teachersid):

    logger.debug('Hello, create_common_share_path.')

    ext_share_path = f'{ext_course_path}/share'
    local_share_path = f'{local_course_path}/share'
    mount_volumes = list()

    # Create
    create_dir(ext_share_path, mode=0o0775, uid=rootid,
               gid=teachersid)

    if role == ROLE_INSTRUCTOR:
        mount_volumes.append(
            {'type': 'bind',
             'source': ext_share_path,
             'target': local_share_path})
    else:
        mount_volumes.append(
            {'type': 'bind',
             'source': ext_share_path,
             'target': local_share_path,
             'ReadOnly': True})

    logger.debug(f'mount_volumes = {str(mount_volumes)}')
    logger.debug('Finish, create_common_share_path.')

    return mount_volumes


def get_course_students(shortname):

    courseid = 0
    active_student_list = []
    studentlist = []

    try:
        # MySQL(Moodleデータベース)に接続
        conn = pymysql.connect(
            database=moodle_database_dbname,
            user=moodle_database_username,
            password=moodle_database_password,
            host=moodle_database_dbhost,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        cur = conn.cursor()

        # 学生ロールのIDを取得
        cur.execute("select id from mdl_role where shortname='student'")
        rows = cur.fetchall()
        for row in rows:
            roleid = row['id']

        # コースIDの値を取得
        cur.execute('select id from mdl_course where shortname=%s', [shortname])
        rows = cur.fetchall()
        for row in rows:
            courseid = int(row['id'])

        if courseid <= 1:
            return active_student_list

        # コースコンテキストの値を取得
        cur.execute(
            """
            select id
            from mdl_context
            where instanceid=%s
            and contextlevel=%s
            """, [courseid, CONTEXTLEVEL_COURSE])
        rows = cur.fetchall()
        for row in rows:
            contextid = int(row['id'])

        if contextid <= 0:
            return active_student_list

        cur.execute("""
                    select
                        u.id,
                        u.username,
                        u.firstname,
                        u.lastname,
                        u.email
                    from
                        (select userid
                        from mdl_role_assignments
                        where contextid=%s
                        and roleid=%s
                        group by userid) a
                        inner join mdl_user u
                        on a.userid=u.id
                        and u.auth='ldap'
                    """, [contextid, roleid])

        rows = cur.fetchall()
        for row in rows:
            studentlist.append(
                dict(id=row['id'],
                     username=row['username'],
                     first_name=row['firstname'],
                     last_name=row['lastname'],
                     email=row['email'],
                     lms_user_id=row['username']))

        enrolids = ''

        cur.execute("""
                    select id
                    from mdl_enrol
                    where courseid=%s
                    and status=0
                    """, [courseid])

        rows = cur.fetchall()
        for row in rows:
            value = int(row['id'])
            if len(enrolids) > 0:
                enrolids = enrolids + ','
            enrolids = enrolids + str(value)

        active_users = []

        stmt_formats = ','.join(['%s'] * len(enrolids))
        stmt = """
                select userid
                from mdl_user_enrolments
                where enrolid in (%s)
                and status=0
                group by userid
                """

        cur.execute(stmt % stmt_formats, tuple(enrolids))
        rows = cur.fetchall()
        for row in rows:
            active_users.append(int(row['userid']))

        for record in studentlist:
            for studentid in active_users:
                if record['id'] == studentid:
                    active_student_list.append(
                        dict(id=record['username'],
                             first_name=record['first_name'],
                             last_name=record['last_name'],
                             email=record['email'],
                             lms_user_id=record['username']))

    except pymysql.Warning as w:
        logger.warn(w)
    finally:
        try:
            # 例外の有無に関わらずカーソルと接続を閉じる
            cur.close()
            conn.close()
        except Exception:
            pass

    return active_student_list


def create_dir(dir, mode=-1, uid=-1, gid=-1):

    # create directory if not exist
    if not os.path.exists(dir):
        os.makedirs(dir)
        logger.debug(f'created directory: {dir}')

    # set permission to directory if specified
    if mode > -1:
        os.chmod(dir, mode)
        logger.debug(f'set {mode} to {dir}')

    # set owner to directory if specified
    if uid > -1 and gid > -1:
        os.chown(dir, uid, gid)
        logger.debug(f'set owner {uid}:{gid} to {dir}')


def create_nbgrader_path(shortname, role, username, rootid, teachersid, studentsid, userid, groupid):

    logger.debug('Hello, create_nbgrader_path.')
    
    # directory name
    server_extension_config_dir = 'jupyter_server_config.d'
    lab_extension_config_dir = 'labconfig'
    
    # file name
    server_extension_config_formgrader = 'nbgrader.server_extensions.formgrader.json'
    server_extension_config_assignment_list = 'nbgrader.server_extensions.assignment_list.json'
    lab_extensions_config = 'page_config.json'
    
    # directory paths for exchange files between users
    exchange_root_path = f'{share_directory_root}/nbgrader/exchange'
    exchange_course_path = f'{exchange_root_path}/{shortname}'
    exchange_inbound_path = f'{exchange_course_path}/inbound'
    exchange_outbound_path = f'{exchange_course_path}/outbound'
    exchange_feedback_path = f'{exchange_course_path}/feedback'

    # directory paths for config file for each user
    user_home = f'{home_directory_root}/{username}'
    user_config_path = f'{user_home}/.jupyter'
    user_labconfig_path = f'{user_config_path}/{lab_extension_config_dir}'
    user_serverextension_config_path = f'{user_config_path}/{server_extension_config_dir}'
    user_notebook_config_file = f'{user_labconfig_path}/page_config.json'
    user_serverextension_config_formgrader = f'{user_serverextension_config_path}/{server_extension_config_formgrader}'
    user_serverextension_config_assignment_list = f'{user_serverextension_config_path}/{server_extension_config_assignment_list}'
      
    nbgrader_template_path_base = f'{share_directory_root}/nbgrader/templates'
    if role == ROLE_INSTRUCTOR:
        nbgrader_template_path = f'{nbgrader_template_path_base}/{DIR_NAME_TEMPLATE_TEACHER}'

    else:
        nbgrader_template_path = f'{nbgrader_template_path_base}/{DIR_NAME_TEMPLATE_STUDENT}'

    # Create exchange root directory
    create_dir(exchange_root_path, mode=0o0755, uid=rootid,
               gid=teachersid)

    # Create user's config directory
    create_dir(user_config_path, mode=0o0755, uid=userid,
               gid=groupid)

    # Create user's serverextension config directory
    create_dir(user_serverextension_config_path, mode=0o0755, uid=userid,
               gid=groupid)

    # Create user's nbconfig directory
    create_dir(user_labconfig_path, mode=0o0755, uid=userid,
               gid=groupid)

    # Remove existing jupyter notebook config file
    if os.path.exists(user_notebook_config_file):
        os.remove(user_notebook_config_file)

    # Remove existing notebook config file
    if os.path.exists(user_serverextension_config_formgrader):
        os.remove(user_serverextension_config_formgrader)

    # Remove existing tree config file
    if os.path.exists(user_serverextension_config_assignment_list):
        os.remove(user_serverextension_config_assignment_list)

    # Create user's notebook and tree config file
    if os.path.exists(user_labconfig_path):
        notebook_template_file = f'{nbgrader_template_path}/{lab_extensions_config}'
        shutil.copyfile(notebook_template_file, user_notebook_config_file)
        os.chown(user_notebook_config_file, userid, groupid)
        os.chmod(user_notebook_config_file, 0o0644)
        
        server_extension_config_assignment_list_template = f'{nbgrader_template_path}/{server_extension_config_assignment_list}'
        shutil.copyfile(server_extension_config_assignment_list_template, user_serverextension_config_assignment_list)
        os.chown(user_serverextension_config_assignment_list, userid, groupid)
        os.chmod(user_serverextension_config_assignment_list, 0o0644)

    if role == ROLE_INSTRUCTOR:
        create_dir(exchange_course_path, mode=0o0755, uid=userid,
                    gid=teachersid)
        create_dir(exchange_inbound_path, mode=0o2733, uid=userid,
                    gid=studentsid)
        create_dir(exchange_outbound_path, mode=0o0755, uid=userid,
                    gid=studentsid)
        create_dir(exchange_feedback_path, mode=0o0711, uid=userid,
                    gid=studentsid)

        server_extension_config_formgrader_template = f'{nbgrader_template_path}/{server_extension_config_formgrader}'
        shutil.copyfile(server_extension_config_formgrader_template, user_serverextension_config_formgrader)
        os.chown(user_serverextension_config_formgrader, userid, groupid)
        os.chmod(user_serverextension_config_formgrader, 0o0644)
        
        instructor_root_path = user_home + '/nbgrader'
        instructor_log_file = instructor_root_path + '/nbgrader.log'
        course_path = instructor_root_path + '/' + shortname
        course_autograded_path = course_path + '/autograded'
        course_release_path = course_path + '/release'
        course_source_path = course_path + '/source'
        course_submitted_path = course_path + '/submitted'
        course_config_file = course_path + '/nbgrader_config.py'
        source_header_file = course_source_path + '/header.ipynb'
        
        config_template_file = nbgrader_template_path + '/nbgrader_config.py'
        header_template_file = nbgrader_template_path + '/header.ipynb'

        # Create root of instructor's local directory
        create_dir(instructor_root_path, mode=-1, uid=userid,
                    gid=teachersid)
        create_dir(course_path, mode=-1, uid=userid, gid=teachersid)
        create_dir(course_autograded_path, mode=0o0755, uid=userid,
                    gid=groupid)
        create_dir(course_release_path, mode=0o0755, uid=userid,
                    gid=groupid)
        create_dir(course_source_path, mode=0o2755, uid=userid,
                    gid=groupid)
        create_dir(course_submitted_path, mode=0o0755, uid=userid,
                    gid=groupid)
        
        # Copy nbgrader's setting file for instructor.
        if os.path.exists(course_path):
            if os.path.exists(course_config_file):
                os.remove(course_config_file)

            dbpath = f'sqlite:////home/{username}/nbgrader/{shortname}/gradebook.db'
            course_root = f"c.CourseDirectory.root = '/home/{username}/nbgrader/{shortname}'"
            db_url = f"c.CourseDirectory.db_url = '{dbpath}'"
            logfile_path = \
                f"c.NbGrader.logfile = '/home/{username}/nbgrader.log'"
            
            # nbgrader_config.py(template)
            with open(config_template_file, encoding="utf-8") as f1:
                target_lines = f1.read()

            # students list
            studentlist = get_course_students(str(shortname))
            target_lines = target_lines.replace(
                'c.CourseDirectory.db_students = []', f"c.CourseDirectory.db_students = {str(studentlist)}")
            
            # gradebook.db
            target_lines = target_lines.replace(
                'gb = Gradebook()', f"gb = Gradebook('{dbpath}', '{shortname}', None)")

            target_lines = target_lines.replace('TemplateCourse', shortname)
            target_lines = target_lines.replace(f"c.CourseDirectory.root = ''", course_root)
            target_lines = target_lines.replace(f"c.CourseDirectory.db_url = ''", db_url)
            target_lines = target_lines.replace(f"c.NbGrader.logfile = ''", logfile_path)

            # nbgrader_config.py(for course)
            with open(course_config_file, mode="w", encoding="utf-8") as f2:
                f2.write(target_lines)
 
            os.chown(course_config_file, userid, groupid)
            os.chmod(course_config_file, 0o0644)

        # Copy header file of source file of assignment.
        if os.path.exists(course_source_path) \
                and not os.path.exists(source_header_file):

            shutil.copyfile(header_template_file, source_header_file)
            os.chown(source_header_file, userid, groupid)
            os.chmod(source_header_file, 0o0644)

        # Truncate instructor's log file
        if os.path.exists(instructor_log_file):
            fp = open(instructor_log_file, 'r+')
            fp.truncate(0)
            fp.close()
            os.chown(instructor_log_file, userid, groupid)
            os.chmod(instructor_log_file, 0o0644)

    logger.debug('Finish, create_nbgrader_path.')


def create_userdata(spawner, auth_state, moodle_username, course_shortname):

    logger.debug('Hello, create_userdata.')

    ext_root_path = f'{share_directory_root}/class'
    ext_course_path = f'{ext_root_path}/{course_shortname}'

    user_home_path = f'{home_directory_root}/{moodle_username}'

    local_base_path = f'{user_home_path}/class'
    local_course_path = f'{local_base_path}/{course_shortname}'

    mount_volumes = []

    change_flag = False

    if type(spawner.extra_container_spec) != dict \
            or 'mounts' not in spawner.extra_container_spec:
        change_flag = True
    elif not spawner.extra_container_spec['mounts']:
        change_flag = True
    elif course_shortname not in str(spawner.extra_container_spec['mounts']) \
            or moodle_username not in str(spawner.extra_container_spec['mounts']):
        change_flag = True
    else:
        logger.debug(
            f"previous mounts = {str(spawner.extra_container_spec['mounts'])}")
        for item in spawner.extra_container_spec['mounts']:
            logger.debug("item = " + str(item))
            if course_shortname in str(item['source']) \
                    and (course_shortname not in str(item['target'])
                         or moodle_username not in str(item['target'])):
                change_flag = True
            elif not os.path.exists(item['source']):
                change_flag = True

    # Must set volume information for user.
    if change_flag:
        try:
            rootobj = pwd.getpwnam("root")
        except KeyError as e:
            logger.error("Could not find root in passwd.")
            raise e
        try:
            teachersobj = grp.getgrnam("teachers")
            studentsobj = grp.getgrnam("students")
        except KeyError as e:
            logger.error("Could not find teachers/students in group.")
            raise e

        rootid = rootobj[2]
        userid = get_ldap_userid(moodle_username)
        groupid = get_ldap_groupid(moodle_username)

        if userid <= 0:
            userid = rootid

        groupid = get_ldap_groupid(moodle_username)

        if userid <= 0:
            groupid = rootid

        teachersid = teachersobj[2]
        studentsid = studentsobj[2]

        if os.path.exists(local_base_path):
            with os.scandir(local_base_path) as it:
                for entry in it:
                    if not entry.name.startswith('.') and entry.is_dir():
                        logger.debug(f"Try to delete {entry.name}")
                        shutil.rmtree(local_base_path + "/" + entry.name)
                        logger.debug(f"Deleted {entry.name}")

            shutil.rmtree(local_base_path)
            logger.debug("Local class directory was deleted.")
            create_dir(local_base_path)
            logger.debug("Local class directory was created.")

        role = get_user_role(auth_state)

        # Create initial mount data.
        mount_volumes = [
            {'type': 'bind',
             'source': user_home_path,
             'target': f'/home/{moodle_username}'}]

        # ldap.conf
        mount_volumes.append(
            {'type': 'bind',
             'source': f'{notebook_template_root}/images/ldap.conf',
             'target': '/etc/ldap.conf',
             'ReadOnly': True})

        if role == ROLE_INSTRUCTOR:
            # Create external course top path.
            create_dir(ext_course_path, mode=0o0775, uid=rootid,
                       gid=teachersid)

        # Create local course top path.
        create_dir(local_course_path, mode=0o0775, uid=rootid,
                   gid=teachersid)

        # Confirm external course top path and local course top path.
        if not os.path.exists(ext_course_path):
            raise CreateDirectoryException(ext_course_path)

        if not os.path.exists(local_course_path):
            raise CreateDirectoryException(local_course_path)

        if os.path.exists(share_directory_root):
            mount_volumes.append(
                {'type': 'bind',
                 'source': share_directory_root,
                 'target': '/jupytershare'})
            logger.debug(str(mount_volumes))

        # Create and mount common share path.
        local_course_path_in_container = f'/home/{moodle_username}/class/{course_shortname}'
        common_volumes = create_common_share_path(
            ext_course_path, local_course_path_in_container, role, rootid, teachersid)

        logger.debug(f'common_volumes = {str(common_volumes)}')

        if type(common_volumes) == list:
            for item in common_volumes:
                if item not in mount_volumes:
                    logger.debug(f'new item = {str(item)}')
                    mount_volumes.append(item)

        # Create and mount nbgrader share path.
        create_nbgrader_path(
            course_shortname, role, moodle_username,
            rootid, teachersid, studentsid, userid, groupid)

        logger.debug(f'mount_volumes = {str(mount_volumes)}')

    logger.debug('create_userdata finised.')
    return mount_volumes


def pass_gen(size=12):
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

    rolelist = auth_state['https://purl.imsglobal.org/spec/lti/claim/roles']
    instructor_flag = False
    learner_flag = False
    role = ''

    # Get user's role.
    for rolename in rolelist:
        type, role = rolename.split('#')
        if not type == 'http://purl.imsglobal.org/vocab/lis/v2/membership':
            continue
        if role == ROLE_INSTRUCTOR:
            instructor_flag = True
        elif role == ROLE_LEARNER:
            learner_flag = True

    if not learner_flag and instructor_flag:
        role = ROLE_INSTRUCTOR
    else:
        role = ROLE_LEARNER

    return role


def validate_user_info(user_info, username):

    try:
        uidNumber, univ_role = user_info
    except Exception as e:
        logger.error(e)
        raise InvalidUserInfoException('get_info() must return 2 values.')

    try:
        uidNumber = int(uidNumber)
    except ValueError:
        raise InvalidUserInfoException('uidNumber must be int')

    if uidNumber < 0:
        raise InvalidUserInfoException('uidNumber must be greater than 0')

    if univ_role is None or univ_role not in EXPECTED_ROLES:
        raise InvalidUserInfoException(
            f'invalid role user:{username} value:{univ_role}')

    return uidNumber, univ_role


def create_home_hook(spawner, auth_state):

    logger.debug('Hello, auth_state_hook.')

    # if authentication information has been received safely.
    if auth_state:
        moodle_username = auth_state['https://purl.imsglobal.org/spec/lti/claim/ext']['user_username']
        course_shortname = auth_state['https://purl.imsglobal.org/spec/lti/claim/context']['label']

        homePath = f'{home_directory_root}/{moodle_username}'

        moodle_role = get_user_role(auth_state)
        uidNumber = -1
        univ_role = moodle_role

        sys.path.append(os.path.dirname(__file__))
        from organization_user import get_info
        logger.debug('start get organization user data')

        user_info = get_info(
            moodle_username, moodle_role, auth_state)

        uidNumber, univ_role = validate_user_info(user_info, moodle_username)

        logger.debug('finish get organization user data')

        if univ_role == ROLE_INSTRUCTOR:
            logger.debug('user = teachers.')
            gidNumber = int(jupyterhub_groupid_teachers)
            loginShell = '/bin/bash'
        else:
            logger.debug('user = students.')
            gidNumber = int(jupyterhub_groupid_students)
            loginShell = '/sbin/nologin'

        search_result = search_local_ldap(moodle_username, ['uidNumber'])

        # The user is already registered in local ldap server.
        if search_result:
            logger.debug(f'User ({moodle_username}) already exists in local ldap.')
        else:
            logger.debug(f'User ({moodle_username}) does not exists.')

            add_local_ldap(
                f'uid={moodle_username},{c.UniversitySwarmSpawner.ldap_base_dn}',
                ['posixAccount', 'inetOrgPerson'],
                {'uid': moodle_username,
                 'cn': moodle_username,
                 'sn': moodle_username,
                 'uidNumber': uidNumber,
                 'gidNumber': gidNumber,
                 'homeDirectory': f'/home/{moodle_username}',
                 'loginShell': loginShell,
                 'userPassword': pass_gen(12),
                 'mail': f'{moodle_username}@{email_domain}'},
            )

            logger.debug(f'User ({moodle_username}) registered to ldap server.')

        # System must create user's home directory.
        if not os.path.isdir(homePath) \
                and not os.path.isfile(homePath):

            logger.debug(f'Try to create {homePath}')
            shutil.copytree(skelton_directory, homePath)
            if os.path.isdir(homePath):
                logger.debug('Try to set owner permission.')
                change_owner(homePath, uidNumber, gidNumber)
        else:
            logger.debug(f'{homePath} already exists.')

        # Set environment variables.
        set_user_environment_variables(spawner, auth_state, moodle_username)

        # Create userdata for subject.
        mount_volumes = create_userdata(spawner, auth_state, moodle_username, course_shortname)

        if type(mount_volumes) == list and len(mount_volumes) != 0:
            logger.debug(f'new mount_volumes = {str(mount_volumes)}')
            spawner.extra_container_spec['mounts'] = mount_volumes
            spawner.extra_container_spec['user'] = '0'

    logger.debug('auth_state_hook finished.')


async def create_dir_hook(spawner):

    username = spawner.user.name
    logger.debug(f'Hello, {username}, pre_spawn_hook.')

    spawner.cmd = ['/usr/local/bin/start-singleuser.sh']
    spawner.args = ['--allow-root', '--user=' + username]

    spawner.image_homedir_format_string = f'{home_directory_root}/{username}'

    logger.debug(str(spawner.get_state()))
    logger.debug('Finish pre_spawn_hook.')


c.UniversitySwarmSpawner.pre_spawn_hook = create_dir_hook
c.UniversitySwarmSpawner.auth_state_hook = create_home_hook
