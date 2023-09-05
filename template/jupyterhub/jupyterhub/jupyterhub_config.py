import base64
import configparser
import copy
import errno
import hashlib
import json
import logging
import os
import pwd
import secrets
import shutil
import string
import sys
import grp

from ldap3 import Server, Connection, ALL
import ldap3.core.exceptions as exceptions
import pymysql.cursors

LOG_FORMAT = "[%(levelname)s %(asctime)s %(module)s %(funcName)s:%(lineno)d] %(message)s"

# logger setting
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(log_formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

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


config_ini = configparser.ConfigParser()
# config_ini_path = 'jupyterhub_config.ini'
config_ini_path = os.path.dirname(__file__) + '/' + 'jupyterhub_config.ini'

# Issue an error code where a config-file does not exist
if not os.path.exists(config_ini_path):
    raise FileNotFoundError(errno.ENOENT, os.strerror(
        errno.ENOENT), config_ini_path)

config_ini.read(config_ini_path, encoding='utf-8')

lti_consumer_key = config_ini.get('LTI', 'Lti_consumer_key')
lti_secret = config_ini.get('LTI', 'Lti_secret')

jupyterhub_admin_users = config_ini.get('JUPYTERHUB', 'Admin_users')
jupyterhub_groupid_teachers = config_ini.get('JUPYTERHUB', 'Groupid_teachers')
jupyterhub_groupid_students = config_ini.get('JUPYTERHUB', 'Groupid_students')

global_ldap_server = config_ini.get('GLOBAL_LDAP', 'Ldap_server')
global_ldap_password = config_ini.get('GLOBAL_LDAP', 'Ldap_password')
global_ldap_base_dn = config_ini.get('GLOBAL_LDAP', 'Ldap_base_dn')

local_ldap_server = config_ini.get('LOCAL_LDAP', 'Ldap_server')
local_ldap_password = config_ini.get('LOCAL_LDAP', 'Ldap_password')
local_ldap_base_dn = config_ini.get('LOCAL_LDAP', 'Ldap_base_dn')
local_ldap_manager_dn = config_ini.get('LOCAL_LDAP', 'Ldap_manager_dn')

database_dbhost = config_ini.get('DATABASE', 'Database_host')
database_username = config_ini.get('DATABASE', 'Database_username')
database_password = config_ini.get('DATABASE', 'Database_password')
database_dbname = config_ini.get('DATABASE', 'Database_dbname')

moodle_database_dbhost = config_ini.get('MOODLE', 'Database_host')
moodle_database_username = config_ini.get('MOODLE', 'Database_username')
moodle_database_password = config_ini.get('MOODLE', 'Database_password')
moodle_database_dbname = config_ini.get('MOODLE', 'Database_dbname')

home_directory_root = config_ini.get('SHARED_DIRECTORY', 'Home_directory_root')
skelton_directory = config_ini.get('SHARED_DIRECTORY', 'Skelton_directory')
nbgrader_exchange_root = config_ini.get(
    'SHARED_DIRECTORY', 'Nbgrader_exchange_root')
nbgrader_template_root = config_ini.get(
    'SHARED_DIRECTORY', 'Nbgrader_template_root')
nbgrader_template_students = config_ini.get(
    'SHARED_DIRECTORY', 'Nbgrader_template_students')
nbgrader_template_teachers = config_ini.get(
    'SHARED_DIRECTORY', 'Nbgrader_template_teachers')
subject_shared_root = config_ini.get('SHARED_DIRECTORY', 'Subject_shared_root')

email_domain = config_ini.get('USER_DATA', 'Email_domain')
mem_guarantee = config_ini.get('RESOURCE', 'Mem_guarantee')
teacher_mem_limit = config_ini.get('RESOURCE', 'Teacher_mem_limit')
student_mem_limit = config_ini.get('RESOURCE', 'Student_mem_limit')
cpu_guarantee = float(config_ini.get('RESOURCE', 'Cpu_guarantee'))
cpu_limit = float(config_ini.get('RESOURCE', 'Cpu_limit'))

notebook_image = config_ini.get('DOCKER', 'Notebook_image')
swarm_network = config_ini.get('DOCKER', 'Swarm_network')

logger.info(lti_consumer_key)
logger.info(lti_secret)
logger.info(jupyterhub_admin_users)
logger.info(jupyterhub_groupid_teachers)
logger.info(jupyterhub_groupid_students)
logger.info(global_ldap_server)
logger.info(global_ldap_password)
logger.info(global_ldap_base_dn)
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
logger.info(skelton_directory)
logger.info(nbgrader_exchange_root)
logger.info(nbgrader_template_root)
logger.info(nbgrader_template_students)
logger.info(nbgrader_template_teachers)
logger.info(subject_shared_root)
logger.info(email_domain)

# Set LTI authenticator.
c.JupyterHub.authenticator_class = 'ltiauthenticator.LTIAuthenticator'
# Set token and secret for LTI v1.1
c.LTI11Authenticator.consumers = {lti_consumer_key: lti_secret}
# Do not create new user when user is authenticated.
c.LTI11Authenticator.create_system_users = False

# Set administrator users.
c.Authenticator.admin_users = json.loads(
    jupyterhub_admin_users.replace("'", '"'))
logger.info(f"adminusers = {str(list(c.Authenticator.admin_users))}")

if 'JUPYTERHUB_CRYPT_KEY' not in os.environ:
    logger.warn(
        "Need JUPYTERHUB_CRYPT_KEY env for persistent auth_state."
        "    export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)"
    )
    c.CryptKeeper.keys = [os.urandom(32)]

# Use auth state parameters.
c.Authenticator.enable_auth_state = True

c.JupyterHub.db_kwargs = {"pool_recycle": 300}

# url for the database. e.g. `sqlite:///jupyterhub.sqlite`
#  Default: 'sqlite:///jupyterhub.sqlite'
# c.JupyterHub.db_url = 'sqlite:///jupyterhub.sqlite'
# Use MySQL (mariadb)
c.JupyterHub.db_url = 'mysql+mysqlconnector://{}:{}@{}/{}{}'.format(
    database_username,
    database_password,
    database_dbhost,
    database_dbname,
    "")

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
    'network_mode': "swarm_jupyterhub-net"}
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


def set_user_environment_variables(spawner, auth_state, username):

    if not auth_state:
        return

    if get_ldap_userid(username) <= 0:
        return

    if not spawner.user.name == username:
        return

    user_home = f'{home_directory_root}/{auth_state["ext_user_username"]}'
    c.Spawner.environment = {
        'MOODLECOURSE': auth_state['context_label'],
        'MPLCONFIGDIR': user_home + '/.cache/matplotlib',
        'TZ': 'Asia/Tokyo',
        'GRANT_SUDO': 'yes',
        'HOME': user_home,
        'PWD': user_home,
        'PATH': f'{user_home}/.local/bin:' +
                f'{user_home}/bin:/usr/local/bin:/usr/local/sbin:' +
                '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin'}

    if "Instructor" == get_user_role(auth_state):
        c.UniversitySwarmSpawner.mem_limit = teacher_mem_limit
    else:
        c.UniversitySwarmSpawner.mem_limit = student_mem_limit


def changeOwner(homePath, uid, gid):
    for root, dirs, files in os.walk(homePath):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
    os.chown(homePath, uid, gid)


def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        logger.error('Directory not copied')
        logger.error(e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        logger.error('Directory not copied')
        logger.error(e)


def search_local_ldap(username, attributes: list):

    try:
        server = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)

        conn = Connection(
            server,
            c.UniversitySwarmSpawner.ldap_manager_dn,
            password=c.UniversitySwarmSpawner.ldap_password,
            read_only=False,
            raise_exceptions=True)
        conn.bind()
        logger.debug("Connect to local ldap server.")

        try:
            conn.search(
                f'uid={username},{c.UniversitySwarmSpawner.ldap_base_dn}',
                '(objectClass=*)',
                attributes=attributes)
        except exceptions.LDAPNoSuchObjectResult:
            logger.warning(f"No such user :{username}")
            return

        return copy.deepcopy(conn.entries)

    except Exception as e:
        raise e
    finally:
        conn.unbind()


def get_ldap_userid(username):

    logger.debug("Hello, get_ldap_userid.")
    attr = 'uidNumber'
    uidNumber = -1

    try:
        search_result = search_local_ldap(username, [attr])
    except Exception as e:
        logger.error("Cannot connect to local ldap server.")
        logger.error(e)
        return uidNumber
    # The user is already registered in local ldap server.
    if search_result:
        logger.debug(f"User {username} already exists in local ldap.")
        logger.debug(str(search_result[0]))
        uidNumber = search_result[0][attr].value

    logger.debug("Finish, get_ldap_userid.")

    return uidNumber


def get_ldap_groupid(username):
    logger.debug("Hello, get_ldap_groupid.")

    attr = 'gidNumber'
    gidNumber = -1

    try:
        search_result = search_local_ldap(username, [attr])
    except Exception as e:
        logger.error("Cannot connect to local ldap server.")
        logger.error(e)
        return gidNumber

    if search_result:
        logger.debug("User (" + username + ") already exists in local ldap.")
        logger.debug(str(search_result[0]))
        gidNumber = search_result[0][attr].value

    logger.debug("Finish, get_ldap_groupid.")
    return gidNumber


def create_common_share_path(ext_course_path, local_course_path, role, rootid, teachersid):

    logger.debug("Hello, create_common_share_path.")

    ext_share_path = ext_course_path + "/share"
    local_share_path = local_course_path + "/share"

    mount_volumes = []

    try:
        if not os.path.exists(ext_share_path):
            os.makedirs(ext_share_path)
        if os.path.exists(ext_share_path):
            os.chown(ext_share_path, rootid, teachersid)
            os.chmod(ext_share_path, 0o775)
    except OSError:
        logger.error("Could not create and set local class directory.")
        return []

    if os.path.exists(ext_share_path):
        if role == "Instructor":
            mount_volumes.append(
                {'type': 'bind',
                 'source': ext_share_path,
                 'target': local_share_path,
                 'mode': 'rw'})
        else:
            mount_volumes.append(
                {'type': 'bind',
                 'source': ext_share_path,
                 'target': local_share_path,
                 'mode': 'ro'})

    logger.debug("mount_volumes = " + str(mount_volumes))
    logger.debug("Finish, create_common_share_path.")

    return mount_volumes


def get_my_connection():

    try:
        conn = pymysql.connect(
            database=moodle_database_dbname,
            user=moodle_database_username,
            password=moodle_database_password,
            host=moodle_database_dbhost,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        logger.error(str(e))
        sys.exit(1)
    except pymysql.Warning as e:
        logger.warn(str(e))
        sys.exit(1)

    return conn


def get_course_students(shortname):

    courseid = 0
    active_student_list = []
    studentlist = []

    try:
        # MySQL(Moodleデータベース)に接続
        conn = get_my_connection()
        cur = conn.cursor()

        # 学生ロールのIDを取得
        cur.execute("select id from mdl_role where shortname='student'")
        rows = cur.fetchall()
        for row in rows:
            roleid = row['id']

        # コースIDの値を取得
        cur.execute(f"select id from mdl_course where shortname='{shortname}'")
        rows = cur.fetchall()
        for row in rows:
            courseid = int(row['id'])

        if courseid <= 1:
            return active_student_list

        # コースコンテキストの値を取得
        cur.execute(
            f"select id from mdl_context where instanceid='{str(courseid)}' and contextlevel=50")
        rows = cur.fetchall()
        for row in rows:
            contextid = int(row['id'])

        if contextid <= 0:
            return active_student_list

        cur.execute(f"""
                    select
                        u.id,
                        u.username,
                        u.firstname,
                        u.lastname,
                        u.email
                    from
                        (select userid
                        from mdl_role_assignments
                        where contextid={str(contextid)}
                        and roleid={str(roleid)}
                        group by userid) a
                        inner join mdl_user u
                        on a.userid=u.id
                        and u.auth='ldap'
                    """)

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

        cur.execute(f"""
                    select id
                    from mdl_enrol
                    where courseid={str(courseid)}
                    and status=0
                    """)

        rows = cur.fetchall()
        for row in rows:
            value = int(row['id'])
            if len(enrolids) > 0:
                enrolids = enrolids + ','
            enrolids = enrolids + str(value)

        active_users = []

        cur.execute(f"""
                    select userid
                    from mdl_user_enrolments
                    where enrolid in ({enrolids})
                    and status=0
                    group by userid
                    """)

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
        # 例外の有無に関わらずカーソルと接続を閉じる
        cur.close()
        conn.close()

    return active_student_list


def create_dir(dir, permission=-1, uid=-1, gid=-1):
    if not os.path.exists(dir):
        os.makedirs(dir)
        logger.debug(f'created directory: {dir}')
        if os.path.exists(dir):
            if permission > -1:
                os.chmod(dir, permission)
                logger.debug(f'set {permission} to {dir}')
            os.chown(dir, uid, gid)
            logger.debug(f'set owner {uid}:{gid} to {dir}')


def create_nbgrader_path(shortname, role, username, rootid, teachersid, studentsid, userid, groupid):

    logger.debug("Hello, create_nbgrader_path.")

    exchange_root_path = nbgrader_exchange_root
    exchange_course_path = exchange_root_path + '/' + shortname
    exchange_inbound_path = exchange_course_path + "/inbound"
    exchange_outbound_path = exchange_course_path + "/outbound"
    exchange_feedback_path = exchange_course_path + "/feedback"

    user_home = home_directory_root + '/' + username

    user_config_path = user_home + '/.jupyter'

    try:
        # Create exchange root directory
        # TODO: 要確認 論文だとroot:root
        create_dir(exchange_root_path, permission=0o0755, uid=rootid,
                   gid=teachersid)

        # Create user's config directory
        user_config_path = user_home + '/.jupyter'
        create_dir(user_config_path, permission=0o0755, uid=userid,
                   gid=groupid)

        # Create user's nbconfig directory
        user_nbconfig_path = user_config_path + '/nbconfig'
        create_dir(user_nbconfig_path, permission=0o0755, uid=userid,
                   gid=groupid)

        # Remove existing jupyter notebook config file
        user_jupyter_config_file = user_config_path \
            + '/jupyter_notebook_config.json'
        if os.path.exists(user_jupyter_config_file):
            os.remove(user_jupyter_config_file)

        # Remove existing notebook config file
        user_notebook_config_file = user_nbconfig_path + '/notebook.json'
        if os.path.exists(user_notebook_config_file):
            os.remove(user_notebook_config_file)

        # Remove existing tree config file
        user_tree_config_file = user_nbconfig_path + '/tree.json'
        if os.path.exists(user_tree_config_file):
            os.remove(user_tree_config_file)

        nbgrader_template_path = nbgrader_template_students

        if role == "Instructor":
            nbgrader_template_path = nbgrader_template_teachers

        # Create user's jupyter notebook config file
        if os.path.exists(user_config_path):
            jupyter_template_file = nbgrader_template_path \
                + '/jupyter_notebook_config.json'
            shutil.copyfile(jupyter_template_file, user_jupyter_config_file)
            os.chown(user_jupyter_config_file, userid, groupid)
            os.chmod(user_jupyter_config_file, 0o0644)

        # Create user's notebook and tree config file
        if os.path.exists(user_nbconfig_path):
            notebook_template_file = nbgrader_template_path + '/notebook.json'
            shutil.copyfile(notebook_template_file, user_notebook_config_file)
            os.chown(user_notebook_config_file, userid, groupid)
            os.chmod(user_notebook_config_file, 0o0644)
            tree_template_file = nbgrader_template_path + '/tree.json'
            shutil.copyfile(tree_template_file, user_tree_config_file)
            os.chown(user_tree_config_file, userid, groupid)
            os.chmod(user_tree_config_file, 0o0644)

        if role == "Instructor":
            # TODO: 要確認 論文だと0o0555
            create_dir(exchange_course_path, permission=0o0755, uid=userid,
                       gid=teachersid)
            create_dir(exchange_inbound_path, permission=0o2733, uid=userid,
                       gid=studentsid)
            create_dir(exchange_outbound_path, permission=0o0755, uid=userid,
                       gid=studentsid)
            create_dir(exchange_feedback_path, permission=0o0711, uid=userid,
                       gid=studentsid)

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
            create_dir(instructor_root_path, permission=-1, uid=userid,
                       gid=teachersid)
            create_dir(course_path, permission=-1, uid=userid, gid=teachersid)
            create_dir(course_autograded_path, permission=0o0755, uid=userid,
                       gid=groupid)
            create_dir(course_release_path, permission=0o0755, uid=userid,
                       gid=groupid)
            create_dir(course_source_path, permission=0o2755, uid=userid,
                       gid=groupid)
            create_dir(course_submitted_path, permission=0o0755, uid=userid,
                       gid=groupid)

            # Copy nbgrader's setting file for instructor.
            if os.path.exists(course_path):
                if os.path.exists(course_config_file):
                    os.remove(course_config_file)

                dbpath = f'sqlite:///{user_home}/nbgrader/{shortname}/gradebook.db'
                course_root = f"c.CourseDirectory.root = '{course_path}'"
                db_url = f"c.CourseDirectory.db_url = '{dbpath}'"
                logfile_path = \
                    f"c.NbGrader.logfile = '{instructor_root_path}/nbgrader.log'"

                fp1 = open(config_template_file, 'r', encoding='utf-8')
                fp2 = open(course_config_file, 'w',  encoding='utf-8')
                lines = fp1.readlines()

                for line in lines:
                    if 'c.CourseDirectory.db_students = []' in line:
                        studentlist = get_course_students(str(shortname))
                        if studentlist and len(studentlist) >= 1:
                            fp2.write('c.CourseDirectory.db_students = [')
                            i = 0
                            for student in studentlist:
                                studentstring = "    dict("
                                studentstring = studentstring + \
                                    "id=\"" + student['id'] + "\", "
                                studentstring = studentstring + "first_name=\"" + \
                                    student['first_name'] + "\", "
                                studentstring = studentstring + "last_name=\"" + \
                                    student['last_name'] + "\", "
                                studentstring = studentstring + \
                                    "email=\"" + student['email'] + "\", "
                                studentstring = studentstring + \
                                    "lms_user_id=\"" + student['id'] + "\")"
                                if i + 1 < len(studentlist):
                                    studentstring = studentstring + ','
                                fp2.write(studentstring + '')
                            fp2.write(']')
                        else:
                            fp2.write(line)
                    elif 'gb = Gradebook(' in line:
                        line = 'gb = Gradebook(\'' + dbpath + \
                            '\', \'' + shortname + '\', None)'
                        fp2.write(line)
                    else:
                        line = line.replace('TemplateCourse', str(shortname))
                        line = line.replace(
                            'c.CourseDirectory.root = \'\'', course_root)
                        line = line.replace(
                            'c.CourseDirectory.db_url = \'\'', db_url)
                        line = line.replace(
                            'c.NbGrader.logfile = \'\'', logfile_path)
                        fp2.write(line)

                fp1.close()
                fp2.close()

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

    except OSError:
        logger.error(
            "Could not create and set external nbgrader directory"
            + f"({exchange_course_path}).")
        return

    logger.debug("Finish, create_nbgrader_path.")

    return


def create_userdata(spawner, auth_state, username):

    logger.debug("Hello, create_userdata.")

    share_root_path = '/jupytershare'

    roles = auth_state['roles']
    rolelist = roles.split(',')

    logger.debug(str(rolelist))

    course_shortname = auth_state['context_label']
    moodle_username = auth_state['ext_user_username']

    ext_root_path = share_root_path + '/class'
    ext_course_path = ext_root_path + "/" + course_shortname

    user_home_path = home_directory_root + '/' + moodle_username

    local_base_path = user_home_path + '/class'
    local_course_path = local_base_path + '/' + course_shortname

    mount_volumes = []

    change_flag = False

    # TODO 条件見直し
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
        except KeyError:
            logger.error("Could not find root in passwd.")
            return []
        try:
            teachersobj = grp.getgrnam("teachers")
            studentsobj = grp.getgrnam("students")
        except KeyError:
            logger.error("Could not find teachers/students in group.")
            return []

        rootid = rootobj[2]
        userid = get_ldap_userid(username)
        groupid = get_ldap_groupid(username)

        if userid <= 0:
            userid = rootid

        groupid = get_ldap_groupid(username)

        if userid <= 0:
            groupid = rootid

        teachersid = teachersobj[2]
        studentsid = studentsobj[2]

        try:
            if os.path.exists(local_base_path):
                with os.scandir(local_base_path) as it:
                    for entry in it:
                        if not entry.name.startswith('.') and entry.is_dir():
                            logger.debug(f"Try {entry.name}")
                            shutil.rmtree(local_base_path + "/" + entry.name)
                            logger.debug(f"Deleted {entry.name}")

                shutil.rmtree(local_base_path)
                logger.debug("Local class directory was deleted.")
                if not os.path.exists(local_base_path):
                    os.makedirs(local_base_path)
                    logger.debug("Local class directory was created.")
        except OSError:
            logger.error("Could not create and set local class directory.")
            return []

        role = get_user_role(auth_state)

        try:
            # Create initial mount data.
            mount_volumes = [
                {'type': 'bind',
                 'source': user_home_path,
                 'target': user_home_path,
                 'mode': 'rw'}]

            if role == "Instructor":
                # Create external course top path.
                if not os.path.exists(ext_course_path):
                    os.makedirs(ext_course_path)
                if os.path.exists(ext_course_path):
                    os.chown(ext_course_path, rootid, teachersid)
                    os.chmod(ext_course_path, 0o775)
            # Create local course top path.
            if not os.path.exists(local_course_path):
                os.makedirs(local_course_path)
            if os.path.exists(local_course_path):
                os.chown(local_course_path, rootid, teachersid)
                os.chmod(local_course_path, 0o775)

            # Confirm external course top path and local course top path.
            if not os.path.exists(ext_course_path):
                logger.error("Could not create external course path.")
                return []

            if not os.path.exists(local_course_path):
                logger.error("Could not create lcoal course path.")
                return []

            if os.path.exists(share_root_path):
                mount_volumes.append(
                    {'type': 'bind',
                     'source': share_root_path,
                     'target': share_root_path,
                     'mode': 'rw'})
                logger.debug(str(mount_volumes))

            # Create and mount common share path.
            common_volumes = create_common_share_path(
                ext_course_path, local_course_path, role, rootid, teachersid)

            logger.debug(f"common_volumes = {str(common_volumes)}")

            if type(common_volumes) == list:
                for item in common_volumes:
                    if item not in mount_volumes:
                        logger.debug("new item = " + str(item))
                        mount_volumes.append(item)

            # Create and mount nbgrader share path.
            create_nbgrader_path(
                course_shortname, role, moodle_username,
                rootid, teachersid, studentsid, userid, groupid)

        except OSError:
            logger.error("Could not create and set class top/share directory.")

        logger.debug(f"mount_volumes = {str(mount_volumes)}")

    logger.debug("create_userdata finised.")

    return mount_volumes


def pass_gen(size=12):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    # 記号を含める場合
    chars += '=+-[]!$():./*'

    random_pass = ''.join(secrets.choice(chars) for _ in range(size))
    salt = os.urandom(4)
    md = hashlib.sha1(random_pass.encode('utf-8'))
    md.update(salt)
    digest_pass = base64.b64encode(
        '{}{}'.format(md.digest(), salt).encode('utf-8'))
    digest_pass = digest_pass.strip()
    random_pass = '{{SSHA}}{}'.format(digest_pass.decode('utf-8'))
    return random_pass


def get_user_role(auth_state):
    roles = auth_state['roles']
    instructor_flag = False
    learner_flag = False
    rolelist = roles.split(',')
    role = ''

    # Get user's role.
    for rolename in rolelist:
        if rolename == 'Instructor':
            instructor_flag = True
        elif rolename == 'Learner':
            learner_flag = True

    if not learner_flag and instructor_flag:
        role = 'Instructor'
    else:
        role = 'Learner'

    return role


def create_home_hook(spawner, auth_state):

    logger.debug("Hello, auth_state_hook.")

    search_local_ldap('admin', ['uidNumber'])

    # if authentication information has been received safely.
    if auth_state:
        moodle_username = auth_state['ext_user_username']
        homePath = f'{home_directory_root}/{moodle_username}'

        moodle_role = get_user_role(auth_state)
        uidNumber = -1

        try:
            sys.path.append(os.path.dirname(__file__))
            from organization_user import get_info
            uidNumber, univ_role = get_info(
                moodle_username, moodle_role, auth_state)
        except Exception as e:
            sys.stderr.write(e)
            sys.stderr.write("cannot get univercity role")
            return

        if uidNumber is None or uidNumber == -1:
            return

        if univ_role is None:
            return

        if univ_role == 'Instructor':
            logger.debug("user = teachers.")
            gidNumber = int(jupyterhub_groupid_teachers)
            loginShell = '/bin/bash'
        else:
            logger.debug("user = students.")
            gidNumber = int(jupyterhub_groupid_students)
            loginShell = '/sbin/nologin'

        localserver = Server(
            c.UniversitySwarmSpawner.ldap_server, get_info=ALL)
        localconn = Connection(
            localserver,
            c.UniversitySwarmSpawner.ldap_manager_dn,
            password=c.UniversitySwarmSpawner.ldap_password,
            read_only=False)
        conn_result = localconn.bind()

        if not conn_result:
            logger.error("Cannot connect to local ldap server.")
            return

        logger.debug("Connect to local ldap server.")
        search_result = localconn.search(
            f'uid={moodle_username},{c.UniversitySwarmSpawner.ldap_base_dn}',
            '(objectClass=*)')
        add_home_flag = False
        # The user is already registered in local ldap server.
        if search_result:
            logger.debug("User (" + moodle_username +
                         ") already exists in local ldap.")
            add_home_flag = True
        else:
            logger.debug("User (" + moodle_username + ") does not exists.")
            email = moodle_username + "@" + email_domain
            randomPass = pass_gen(12)
            add_result = localconn.add(
                f'uid={moodle_username},{c.UniversitySwarmSpawner.ldap_base_dn}',
                ['posixAccount', 'inetOrgPerson'],
                {'uid': moodle_username,
                 'cn': moodle_username,
                 'sn': moodle_username,
                 'uidNumber': uidNumber,
                 'gidNumber': gidNumber,
                 'homeDirectory': homePath,
                 'loginShell': loginShell,
                 'userPassword': randomPass,
                 'mail': email})

            if not add_result:
                logger.error("Could not register new user to ldap server.")
                return

            add_home_flag = True
            logger.debug("User (" + moodle_username +
                         ") has been registered to ldap server.")

        localconn.unbind()

        # System must create user's home directory.
        if add_home_flag and not os.path.isdir(homePath) \
                and not os.path.isfile(homePath):

            logger.debug("Try to create " + homePath + ".")
            copyDirectory(skelton_directory, homePath)
            if os.path.isdir(homePath):
                logger.debug("Try to set owner premission.")
                changeOwner(homePath, uidNumber, gidNumber)
        else:
            logger.debug(homePath + " already exists.")

        # Set environment variables.
        set_user_environment_variables(spawner, auth_state, moodle_username)

        # Create userdata for subject.
        mount_volumes = create_userdata(spawner, auth_state, moodle_username)

        if type(mount_volumes) == list and len(mount_volumes) != 0:
            logger.debug("new mount_volumes = " + str(mount_volumes))
            spawner.extra_container_spec['mounts'] = mount_volumes
            spawner.extra_container_spec['user'] = '0'

        role = get_user_role(auth_state)

        spawner.environment = {
            'MOODLECOURSE': auth_state['context_label'],
            'COURSEROLE': role,
            'MPLCONFIGDIR': homePath + '/.cache/matplotlib',
            'TZ': 'Asia/Tokyo',
            'GRANT_SUDO': 'yes',
            'HOME': homePath,
            'PWD': homePath,
            'PATH': f'{homePath}/.local/bin:'
                    + f'{homePath}/bin:/usr/local/bin:/usr/local/sbin:'
                    + '/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin'}

    logger.debug("auth_state_hook finished.")


c.UniversitySwarmSpawner.auth_state_hook = create_home_hook


def create_dir_hook(spawner):
    username = spawner.user.name

    logger.debug(f"Hello, {username}, pre_spawn_hook.")

    spawner.cmd = ['/usr/local/bin/start-singleuser.sh']
    spawner.args = ['--allow-root', '--user=' + username]

    spawner.image_homedir_format_string = f'{home_directory_root}/{username}'

    logger.debug(str(spawner.get_state()))
    logger.debug("Finish pre_spawn_hook.")


c.UniversitySwarmSpawner.pre_spawn_hook = create_dir_hook
