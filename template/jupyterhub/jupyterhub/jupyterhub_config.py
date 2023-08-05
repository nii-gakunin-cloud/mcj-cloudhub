import sys,os
from jupyter_client.localinterfaces import public_ips
import json

# The proxy is in another container
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = 'http://proxy:8001'
# tell the hub to use Dummy Auth (for testing)
# c.JupyterHub.authenticator_class = 'dummy'

# The Hub should listen on all interfaces,
# so user servers can connect
c.JupyterHub.hub_ip = '0.0.0.0'
# this is the name of the 'service' in docker-compose.yml
c.JupyterHub.hub_connect_ip = 'hub'
# Initialize processing timeout for spawners.
c.JupyterHub.init_spawners_timeout = 60
# Set max-age day(s) to keep cookie.
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
import logging

c.JupyterHub.log_level = logging.DEBUG
# c.JupyterHub.log_level = logging.ERROR

## Whole system resource restrictions.
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

import configparser
import os
import errno

config_ini = configparser.ConfigParser()
# config_ini_path = 'jupyterhub_config.ini'
config_ini_path = os.path.dirname(__file__) + '/' + 'jupyterhub_config.ini'

# Issue an error code where a config-file does not exist
if not os.path.exists(config_ini_path):
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_ini_path)

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
nbgrader_exchange_root = config_ini.get('SHARED_DIRECTORY', 'Nbgrader_exchange_root')
nbgrader_template_root = config_ini.get('SHARED_DIRECTORY', 'Nbgrader_template_root')
nbgrader_template_students = config_ini.get('SHARED_DIRECTORY', 'Nbgrader_template_students')
nbgrader_template_teachers = config_ini.get('SHARED_DIRECTORY', 'Nbgrader_template_teachers')
subject_shared_root = config_ini.get('SHARED_DIRECTORY', 'Subject_shared_root')

email_domain = config_ini.get('USER_DATA', 'Email_domain')
mem_guarantee = config_ini.get('RESOURCE', 'Mem_guarantee')
teacher_mem_limit = config_ini.get('RESOURCE', 'Teacher_mem_limit')
student_mem_limit = config_ini.get('RESOURCE', 'Student_mem_limit')
cpu_guarantee = float(config_ini.get('RESOURCE', 'Cpu_guarantee'))
cpu_limit = float(config_ini.get('RESOURCE', 'Cpu_limit'))

notebook_image = config_ini.get('DOCKER', 'Notebook_image')
swarm_network = config_ini.get('DOCKER', 'Swarm_network')

if c.JupyterHub.log_level < 30:
    sys.stderr.write(lti_consumer_key + "\n")
    sys.stderr.write(lti_secret + "\n")
    sys.stderr.write(jupyterhub_admin_users + "\n")
    sys.stderr.write(jupyterhub_groupid_teachers + "\n")
    sys.stderr.write(jupyterhub_groupid_students + "\n")
    sys.stderr.write(global_ldap_server + "\n")
    sys.stderr.write(global_ldap_password + "\n")
    sys.stderr.write(global_ldap_base_dn + "\n")
    sys.stderr.write(local_ldap_server + "\n")
    sys.stderr.write(local_ldap_password + "\n")
    sys.stderr.write(local_ldap_base_dn + "\n")
    sys.stderr.write(local_ldap_manager_dn + "\n")
    sys.stderr.write(database_dbhost + "\n")
    sys.stderr.write(database_username + "\n")
    sys.stderr.write(database_password + "\n")
    sys.stderr.write(database_dbname + "\n")
    sys.stderr.write(moodle_database_dbhost + "\n")
    sys.stderr.write(moodle_database_username + "\n")
    sys.stderr.write(moodle_database_password + "\n")
    sys.stderr.write(moodle_database_dbname + "\n")
    sys.stderr.write(home_directory_root + "\n")
    sys.stderr.write(skelton_directory + "\n")
    sys.stderr.write(nbgrader_exchange_root + "\n")
    sys.stderr.write(nbgrader_template_root + "\n")
    sys.stderr.write(nbgrader_template_students + "\n")
    sys.stderr.write(nbgrader_template_teachers + "\n")
    sys.stderr.write(subject_shared_root + "\n")
    sys.stderr.write(email_domain + "\n")

# Set LTI authenticator.
c.JupyterHub.authenticator_class = 'ltiauthenticator.LTIAuthenticator'
# Set token and secret for LTI v1.1
c.LTI11Authenticator.consumers = { lti_consumer_key: lti_secret }
# Do not create new user when user is authenticated.
c.LTI11Authenticator.create_system_users = False

# Set administrator users.
#c.Authenticator.admin_users = { 'admin' }
# Allow login to certaion users.
# c.Authenticator.allowed_users = set()

# c.Authenticator.admin_users = set()
# adminuserlist = jupyterhub_admin_users.split(',')
# for adminuser in adminuserlist:
#     c.Authenticator.admin_users.add(adminuser)

c.Authenticator.admin_users = json.loads(jupyterhub_admin_users.replace("'", '"'))
if c.JupyterHub.log_level < 30:
    sys.stderr.write("adminusers = " + str(list(c.Authenticator.admin_users)) + "\n")

import os
import warnings
if 'JUPYTERHUB_CRYPT_KEY' not in os.environ:
    warnings.warn(
        "Need JUPYTERHUB_CRYPT_KEY env for persistent auth_state.\n"
        "    export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)"
    )
    c.CryptKeeper.keys = [ os.urandom(32) ]

# Use auth state parameters.
c.Authenticator.enable_auth_state = True

c.JupyterHub.db_kwargs = {"pool_recycle" : 300}

## url for the database. e.g. `sqlite:///jupyterhub.sqlite`
#  Default: 'sqlite:///jupyterhub.sqlite'
# c.JupyterHub.db_url = 'sqlite:///jupyterhub.sqlite'
# Use MySQL (mariadb)
c.JupyterHub.db_url = 'mysql+mysqlconnector://{}:{}@{}/{}{}'.format(database_username, database_password, database_dbhost, database_dbname,"")

# Use UniversitySwarmSpawner.
c.JupyterHub.spawner_class = 'dockerspawner.UniversitySwarmSpawner'
# Set home directory path.
c.UniversitySwarmSpawner.host_homedir_format_string = home_directory_root + '/{username}'

# Image of Noetbook
#c.UniversitySpawner.image = 'jupyter_yamaguchi:1.5'
c.UniversitySwarmSpawner.image = notebook_image
#c.UniversitySwarmSpawner.image = 'jupyterhub/singleuser:1.4'

# this is the network name for jupyterhub in docker-compose.yml
# with a leading 'swarm_' that docker-compose adds
c.UniversitySwarmSpawner.network_name = 'swarm_jupyterhub-net'
c.UniversitySwarmSpawner.extra_host_config = { 'network_mode': "swarm_jupyterhub-net" }
c.UniversitySwarmSpawner.extra_placement_spec = { 'constraints': ['node.role == worker'] } 

c.UniversitySwarmSpawner.debug = True

# increase launch timeout because initial image pulls can take a while
c.UniversitySwarmSpawner.start_timeout = 300

c.UniversitySwarmSpawner.ldap_server = local_ldap_server
c.UniversitySwarmSpawner.ldap_password = local_ldap_password
c.UniversitySwarmSpawner.ldap_base_dn = local_ldap_base_dn
c.UniversitySwarmSpawner.ldap_manager_dn = local_ldap_manager_dn

# c.UniversitySwarmSpawner.format_volume_name = '/home/{username}'

c.UniversitySwarmSpawner.image_homedir_format_string = home_directory_root + '/{username}'

# c.UniversirtSwarmSpawner.notebook_dir = '/home/{username}'

c.DockerSpawner.remove_containers = True

#c.DockerSpawner.extra_create_kwargs = { "command": 'env PATH="/opt/conda/bin:/usr/bin:/usr/local/bin" USER="{username}" /usr/local/bin/start-singleuser.sh', }

#c.Spawner.name_template = '{prefix}_{username}__{servername}'
c.Spawner.escape = 'legacy'

# c.DockerSpawner.remove = True

# Start jupyterlab.
#c.Spawner.cmd = ["jupyter", "labhub"]
# Start jupyter notebook for single user.
c.UniversitySwarmSpawner.cmd = ['/usr/local/bin/start-singleuser.sh']
c.UniversitySwarmSpawner.args = [ '--allow-root' ]
#c.DockerSpawner.extra_create_kwargs = { "command": 'env PATH="/opt/conda/bin:/usr/bin:/usr/local/bin" USER="{username}" /usr/local/bin/start-singleuser.sh', }

# Resource allcation restcirtion per user (for image test server).
#c.UniversitySwarmSpawner.cpu_guarantee = 0.5
#c.UniversitySwarmSpawner.cpu_limit = 1.0
#c.UniversitySwarmSpawner.mem_guarantee = '256M'
#c.UniversitySwarmSpawner.mem_limit = '512M'

# Resource allocation restriction per user (for production server).
c.UniversitySwarmSpawner.cpu_guarantee = cpu_guarantee
c.UniversitySwarmSpawner.cpu_limit = cpu_limit

# teacher_mem_limit = '1024M'
# student_mem_limit = '512M'

c.UniversitySwarmSpawner.mem_guarantee = mem_guarantee
c.UniversitySwarmSpawner.mem_limit = student_mem_limit

# Set other services.
#c.JupyterHub.services = [
#    {
#        'name': 'idle-culler',
#        'admin': True,
#        'command': [sys.executable, '-m', 'jupyterhub_idle_culler', '--cull-every=60', '--timeout=1200', '--max-age=3600', '--cull-users=False']
#    }
#]

c.Authenticator.enable_auth_state = True

def set_user_environment_variables(spawner, auth_state, username, uidNumber, gidNumber):
    # Set environment variables.
    if auth_state and get_ldap_userid(username) > 0 and spawner.user.name == username:
        user_home = home_directory_root + '/' +  auth_state['ext_user_username']
        c.Spawner.environment = { 'MOODLECOURSE': auth_state['context_label'], 'MPLCONFIGDIR': user_home + '/.cache/matplotlib' , 'TZ': 'Asia/Tokyo', 'GRANT_SUDO': 'yes', 'HOME': user_home, 'PWD': user_home, 'PATH': user_home + '/.local/bin:' + user_home + '/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin'}

        role = get_user_role(auth_state)

        if role == "Instructor":
            c.UniversitySwarmSpawner.mem_limit = teacher_mem_limit
        else:
            c.UniversitySwarmSpawner.mem_limit = student_mem_limit

import os
def changeOwner(homePath, uid, gid):
    for root, dirs, files in os.walk(homePath):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)
    os.chown(homePath, uid, gid)

import shutil
import sys
def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        sys.stderr.write('Directory not copied. Error: %s\n' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        sys.stderr.write('Directory not copied. Error: %s\n' % e)

from ldap3 import Server, Connection, ALL
import sys
def get_ldap_userid(username):
    if c.JupyterHub.log_level < 30:
      sys.stderr.write("Hello, get_ldap_userid.\n")

    uidNumber = -1

    localserver = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)
    localconn = Connection(localserver, c.UniversitySwarmSpawner.ldap_manager_dn, password=c.UniversitySwarmSpawner.ldap_password, read_only=False)
    conn_result = localconn.bind()
    # if connection to local ldap server succeeded.
    if not conn_result:
        sys.stderr.write("Cannot connect to local ldap server.\n")
    else:
        if c.JupyterHub.log_level < 30:
            sys.stderr.write("Connect to local ldap server.\n")
        search_result = localconn.search('uid=' + username + ',' + c.UniversitySwarmSpawner.ldap_base_dn, '(objectClass=*)', attributes=['uidNumber'])
        # The user is already registered in local ldap server.
        if search_result:
            if c.JupyterHub.log_level < 30:
                sys.stderr.write("User (" + username + ") already exists in local ldap.\n")
                sys.stderr.write(str(localconn.entries[0]) + "\n")
            uidNumber = localconn.entries[0]['uidNumber'].value
        localconn.unbind()

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Finish, get_ldap_userid.\n")

    return uidNumber

from ldap3 import Server, Connection, ALL
import sys
def get_ldap_groupid(username):
    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, get_ldap_groupid.\n")

    gidNumber = -1

    localserver = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)
    localconn = Connection(localserver, c.UniversitySwarmSpawner.ldap_manager_dn, password=c.UniversitySwarmSpawner.ldap_password, read_only=False)
    conn_result = localconn.bind()
    # if connection to local ldap server succeeded.
    if not conn_result:
        sys.stderr.write("Cannot connect to local ldap server.\n")
    else:
        if c.JupyterHub.log_level < 30:
            sys.stderr.write("Connect to local ldap server.\n")
        search_result = localconn.search('uid=' + username + ',' + c.UniversitySwarmSpawner.ldap_base_dn, '(objectClass=*)', attributes=['gidNumber'])
        # The user is already registered in local ldap server.
        if search_result:
            if c.JupyterHub.log_level < 30:
                sys.stderr.write("User (" + username + ") already exists in local ldap.\n")
                sys.stderr.write(str(localconn.entries[0]) + "\n")
            gidNumber = localconn.entries[0]['gidNumber'].value
        localconn.unbind()

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Finish, get_ldap_groupid.\n")

    return gidNumber

import os, sys
def create_common_share_path(ext_course_path, local_course_path, role, rootid, teachersid):
    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, create_common_share_path.\n")

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
        sys.stderr.write("Error: Could not create and set local class directory.\n")
        return []

    if os.path.exists(ext_share_path):
        if role == "Instructor":
            mount_volumes.append({'type': 'bind', 'source': ext_share_path, 'target': local_share_path, 'mode': 'rw' })
        else:
            mount_volumes.append({'type': 'bind', 'source': ext_share_path, 'target': local_share_path, 'mode': 'ro' })

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("mount_volumes = " + str(mount_volumes) + "\n")
        sys.stderr.write("Finish, create_common_share_path.\n")

    return mount_volumes

import pymysql.cursors, sys
## MySQLデータベース(moodle)に接続する関数
def get_my_connection():
    database = moodle_database_dbname
    user = moodle_database_username
    password = moodle_database_password
    host = moodle_database_dbhost

    error_message = 'Cannot connect moodle database.\n'

    try:
        conn = pymysql.connect(
                database = database,
                user = user,
                password = password,
                host = host,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        sys.stderr.write('Catch error: ' + str(e))
        sys.exit(1)
    except pymysql.Warning as w:
        sys.stderr.write('Catch warning: ' + str(e))
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
            roleid=row['id']

        # コースIDの値を取得
        cur.execute("select id from mdl_course where shortname='" + shortname + "'")
        rows = cur.fetchall()
        for row in rows:
            courseid=int(row['id'])

        if courseid <= 1:
            return active_student_list

        # コースコンテキストの値を取得
        cur.execute("select id from mdl_context where instanceid='" + str(courseid) + "'")
        rows = cur.fetchall()
        for row in rows:
            contextid=int(row['id'])

        if contextid <= 0:
            return active_student_list

        cur.execute("select u.id, u.username, u.firstname, u.lastname, u.email from (select userid from mdl_role_assignments where contextid=" + str(contextid) + " and roleid=" + str(roleid) + " group by userid) a inner join mdl_user u on a.userid=u.id and u.auth='ldap'")

        rows = cur.fetchall()
        for row in rows:
            studentlist.append(dict(id=row['id'], username=row['username'], first_name=row['firstname'], last_name=row['lastname'], email=row['email'], lms_user_id=row['username']))

        enrolids = ''

        cur.execute("select id from mdl_enrol where courseid=" + str(courseid) + " and status=0")

        rows = cur.fetchall()
        for row in rows:
            value = int(row['id'])
            if len(enrolids) > 0:
                enrolids = enrolids + ','
            enrolids = enrolids + str(value)

        active_users = []

        cur.execute('select userid from mdl_user_enrolments where enrolid in ('  + enrolids + ') and status=0 group by userid')

        rows = cur.fetchall()
        for row in rows:
            active_users.append(int(row['userid']))

        for record in studentlist:
            for studentid in active_users:
                if record['id'] == studentid:
                    active_student_list.append(dict(id=record['username'], first_name=record['first_name'], last_name=record['last_name'], email=record['email'], lms_user_id=record['username']))

    except pymysql.Warning as w:
        print('Catch warning: ', w)
    finally:
        # 例外の有無に関わらずカーソルと接続を閉じる
        cur.close()
        conn.close()

    return active_student_list

import os, sys, shutil, re
def create_nbgrader_path(shortname, local_course_path, role, username, rootid, teachersid, studentsid, userid, groupid):

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, create_nbgrader_path.\n")

    exchange_root_path = nbgrader_exchange_root
    exchange_course_path = exchange_root_path + '/' + shortname
    exchange_inbound_path = exchange_course_path + "/inbound"
    exchange_outbound_path = exchange_course_path + "/outbound"
    exchange_feedback_path = exchange_course_path + "/feedback"

    user_home = home_directory_root + '/' + username

    user_config_path = user_home + '/.jupyter'

    try:
        # Create exchange root directory
        if not os.path.exists(exchange_root_path):
            os.makedirs(exchange_root_path)
            if os.path.exists(exchange_root_path):
                os.chown(exchange_root_path, rootid, teachersid)
                os.chmod(exchange_root_path, 0o0755)

        # Create uesr's config directory
        user_config_path = user_home + '/.jupyter'
        if not os.path.exists(user_config_path):
            os.makedirs(user_config_path)
            if os.path.exists(user_config_path):
                os.chown(user_config_path, userid, groupid)
                os.chmod(user_config_path, 0o0755)

        # Create user's nbconfig directory
        user_nbconfig_path = user_config_path + '/nbconfig'
        if not os.path.exists(user_nbconfig_path):
            os.makedirs(user_nbconfig_path)
            if os.path.exists(user_nbconfig_path):
                os.chown(user_nbconfig_path, userid, groupid)
                os.chmod(user_nbconfig_path, 0o0755)

        # Remove existing jupyter notebook config file
        user_jupyter_config_file = user_config_path + '/jupyter_notebook_config.json'
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
            jupyter_template_file = nbgrader_template_path + '/jupyter_notebook_config.json'
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
            if not os.path.exists(exchange_course_path):
                os.makedirs(exchange_course_path)
            if os.path.exists(exchange_course_path):
                os.chown(exchange_course_path, userid, teachersid)
                os.chmod(exchange_course_path, 0o0755)
            # Create inbound directory for course
            if not os.path.exists(exchange_inbound_path):
                os.makedirs(exchange_inbound_path)
            if os.path.exists(exchange_inbound_path):
                os.chown(exchange_inbound_path, userid, studentsid)
                os.chmod(exchange_inbound_path, 0o2733)
            # Create outbound directory for couse
            if not os.path.exists(exchange_outbound_path):
                os.makedirs(exchange_outbound_path)
            if os.path.exists(exchange_outbound_path):
                os.chown(exchange_outbound_path, userid, studentsid)
                os.chmod(exchange_outbound_path, 0o0755)
            # Create feedback directory for course
            if not os.path.exists(exchange_feedback_path):
                os.makedirs(exchange_feedback_path)
            if os.path.exists(exchange_feedback_path):
                os.chown(exchange_feedback_path, userid, studentsid)
                os.chmod(exchange_feedback_path, 0o0711)

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
            if not os.path.exists(instructor_root_path):
                os.makedirs(instructor_root_path)
                os.chown(instructor_root_path, userid, teachersid)
            if os.path.exists(instructor_root_path):
                # Create course directory
                if not os.path.exists(course_path):
                    os.makedirs(course_path)
                    os.chown(course_path, userid, teachersid)
            if os.path.exists(course_path):
                # Create autograded directory
                if not os.path.exists(course_autograded_path):
                    os.makedirs(course_autograded_path)
                # Create release directory
                if not os.path.exists(course_release_path):
                    os.makedirs(course_release_path)
                # Create source directory
                if not os.path.exists(course_source_path):
                    os.makedirs(course_source_path)
                # Create submitted directory
                if not os.path.exists(course_submitted_path):
                    os.makedirs(course_submitted_path)

            # Set permissions for instructor's course directories.
            if os.path.exists(course_autograded_path):
                os.chown(course_autograded_path, userid, groupid)
                os.chmod(course_autograded_path, 0o0755)
            if os.path.exists(course_release_path):
                os.chown(course_release_path, userid, groupid)
                os.chmod(course_release_path, 0o0755)
            if os.path.exists(course_source_path):
                os.chown(course_source_path, userid, groupid)
                os.chmod(course_source_path, 0o2755)
            if os.path.exists(course_submitted_path):
                os.chown(course_submitted_path, userid, groupid)
                os.chmod(course_submitted_path, 0o0755)

            # Copy nbgrader's setting file for instructor.
            if os.path.exists(course_path):
                if os.path.exists(course_config_file):
                    os.remove(course_config_file)

                dbpath = 'sqlite:///' + user_home + '/nbgrader/' + shortname + '/gradebook.db'
                course_root = 'c.CourseDirectory.root = \'' + course_path + '\''
                db_url = 'c.CourseDirectory.db_url = \'' + dbpath + '\''
                logfile_path = 'c.NbGrader.logfile = \'' + instructor_root_path + '/nbgrader.log\''

                fp1 = open(config_template_file, 'r', encoding='utf-8')
                fp2 = open(course_config_file, 'w',  encoding='utf-8')
                lines = fp1.readlines()
 
                for line in lines:
                    if 'c.CourseDirectory.db_students = []' in line:
                        studentlist = get_course_students(str(shortname))
                        if studentlist and len(studentlist) >=1:
                            fp2.write('c.CourseDirectory.db_students = [\n')
                            i = 0
                            for student in studentlist:
                                studentstring = "    dict("
                                studentstring = studentstring + "id=\"" + student['id'] + "\", "
                                studentstring = studentstring + "first_name=\"" + student['first_name'] + "\", "
                                studentstring = studentstring + "last_name=\"" + student['last_name'] + "\", "
                                studentstring = studentstring + "email=\"" + student['email'] + "\", "
                                studentstring = studentstring + "lms_user_id=\"" + student['id'] + "\")"
                                if i + 1 < len(studentlist):
                                    studentstring = studentstring + ','
                                fp2.write(studentstring + '\n')
                            fp2.write(']\n')
                        else:
                            fp2.write(line)
                    elif 'gb = Gradebook(' in line:
                        line = 'gb = Gradebook(\'' + dbpath + '\', \'' + shortname + '\', None)\n'
                        fp2.write(line)
                    else:
                        line = line.replace('TemplateCourse', str(shortname))
                        line = line.replace('c.CourseDirectory.root = \'\'', course_root)
                        line = line.replace('c.CourseDirectory.db_url = \'\'', db_url)
                        line = line.replace('c.NbGrader.logfile = \'\'', logfile_path)
                        fp2.write(line)

                fp1.close()
                fp2.close()

                os.chown(course_config_file, userid, groupid)
                os.chmod(course_config_file, 0o0644)

            # Copy header file of source file of assignment.
            if os.path.exists(course_source_path) and not os.path.exists(source_header_file):
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

#        if role == "Learner":
#        learner_nbgrader_path = '/home/' + username + '/' + shortname
#        if not os.path.exists(learner_nbgrader_path):
#            os.makedirs(learner_nbgrader_path)
#        if os.path.exists(learner_nbgrader_path):
#            os.chown(learner_nbgrader_path, userid, groupid)
#            os.chmod(learner_nbgrader_path, 0o0755)

    except OSError:
        sys.stderr.write("Error: Could not create and set external nbgrader directory (" +  exchange_course_path + ").\n")
        return False

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Finish, create_nbgrader_path.\n")

    return True

import os, sys, shutil
def create_userdata(spawner, auth_state, username):

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, create_userdata.\n")

    share_root_path = '/jupytershare'

    roles = auth_state['roles']
    rolelist = roles.split(',')

    if c.JupyterHub.log_level < 30:
        sys.stderr.write(str(rolelist) + "\n")

    course_shortname = auth_state['context_label']
    moodle_username = auth_state['ext_user_username']

    ext_root_path = share_root_path + '/class'
    ext_course_path = ext_root_path + "/" + course_shortname
    ext_share_path =  ext_course_path + "/share"

    user_home_path = home_directory_root + '/' + moodle_username

    local_base_path = user_home_path + '/class';
    local_course_path = local_base_path + '/' + course_shortname
    local_share_path = local_course_path + '/share';
    local_user_path = local_course_path + '/' + moodle_username

    mount_volumes = []

    change_flag = False

    if type(spawner.extra_container_spec) != dict or not 'mounts' in spawner.extra_container_spec:
        change_flag = True
    elif not spawner.extra_container_spec['mounts']:
        change_flag = True
    elif not course_shortname in str(spawner.extra_container_spec['mounts']) or not moodle_username in str(spawner.extra_container_spec['mounts']):
        change_flag = True
    else:
        sys.stderr.write("previous mounts = " + str(spawner.extra_container_spec['mounts']) + "\n")
        for item in spawner.extra_container_spec['mounts']:
            sys.stderr.write("item = " + str(item) + "\n")
            if course_shortname in str(item['source']) and (not course_shortname in str(item['target']) or not moodle_username in str(item['target'])):
                change_flag = True
            elif not os.path.exists(item['source']):
                chang_flag = True

    # Must set volume information for user.
    if change_flag:
        try:
            rootobj = pwd.getpwnam("root")
        except KeyError:
            sys.stderr.write("Error: Could not find root in passwd.\n")
            return []
        try:
            teachersobj = grp.getgrnam("teachers")
            studentsobj = grp.getgrnam("students")
        except KeyError:
            sys.stderr.write("Error: Could not find teachers/students in group.\n")
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
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write("Try " + entry.name + "\n")
#                            os.rmdir(local_base_path + "/" + entry.name)
                            shutil.rmtree(local_base_path + "/" + entry.name)
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write("Deleted " + entry.name + "\n")
#               os.rmdir(local_base_path)
                shutil.rmtree(local_base_path)
                if c.JupyterHub.log_level < 30:
                    sys.stderr.write("Local class directory was deleted.\n")
                if not os.path.exists(local_base_path):
                    os.makedirs(local_base_path)
                    if c.JupyterHub.log_level < 30:
                        sys.stderr.write("Local class directory was created.\n")
        except OSError:
            sys.stderr.write("Error: Could not create and set local class directory.\n")
            return []

        role = ""

        # Get user's role.
#        for rolename in rolelist:
#            if rolename == "Instructor":
#                role = "Instructor"
#            elif rolename == "Learner" and role != "Instructor":
#                role = "Learner"

        role = get_user_role(auth_state)

        try:
            # Create initial mount data.
            mount_volumes = [{'type': 'bind', 'source': user_home_path, 'target': user_home_path, 'mode': 'rw'}]

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
                sys.stderr.write("Error: Could not create external course path.\n")
                return []

            if not os.path.exists(local_course_path):
                sys.stderr("Error: Could not create lcoal course path.\n")
                return []

            if os.path.exists(share_root_path):
                mount_volumes.append({'type': 'bind', 'source': share_root_path, 'target': share_root_path, 'mode': 'rw' })
                if c.JupyterHub.log_level < 30:
                    sys.stderr.write(str(mount_volumes) + "\n")

            # Create and mount common share path.
            common_volumes = create_common_share_path(ext_course_path, local_course_path, role, rootid, teachersid)

            if c.JupyterHub.log_level < 30:
                sys.stderr.write("common_volumes = " + str(common_volumes) + "\n")

            if type(common_volumes) == list:
                for item in common_volumes:
                    if not item in mount_volumes:
                        if c.JupyterHub.log_level < 30:
                            sys.stderr.write("new item = " + str(item) + "\n")
                        mount_volumes.append(item)

            # Create and mount nbgrader share path.
            nbgrader_volumes = create_nbgrader_path(course_shortname, local_course_path, role, moodle_username, rootid, teachersid, studentsid, userid, groupid)

            #if len(nbgrader_volumes) != 0:
            #    mount_volumes.append(nbgrader_volumes)

            # Mount course whole folder for teacher.
#            if role == "Instructor":
#                c.DockerSpawner.volumes[ ext_course_path ] = { 'bind': local_course_path, 'mode': 'rw' }

        except OSError:
            sys.stderr.write("Error: Could not create and set class top/share directory.\n")

        if c.JupyterHub.log_level < 30:
            sys.stderr.write("mount_volumes = " + str(mount_volumes) + "\n")

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("create_userdata finised.\n")

    return mount_volumes

import os, string
import secrets, hashlib, base64
def pass_gen(size=12):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    # 記号を含める場合
    chars += '=+-[]!$():./*'

    random_pass = ''.join(secrets.choice(chars) for x in range(size))
    salt = os.urandom(4)
    md = hashlib.sha1(random_pass.encode('utf-8'))
    md.update(salt)
    digest_pass = base64.b64encode('{}{}'.format(md.digest(), salt).encode('utf-8'))
    digest_pass = digest_pass.strip()
    random_pass = '{{SSHA}}{}'.format(digest_pass.decode('utf-8'))
    return random_pass

def get_user_role(auth_state):
    roles = auth_state['roles']
    instructor_flag = 0
    learner_flag = 0
    rolelist = roles.split(',')
    role = ''

    # Get user's role.
    for rolename in rolelist:
        if rolename == 'Instructor':
            instructor_flag = 1
        elif rolename == 'Learner':
            learner_flag = 1

    if learner_flag == 0 and instructor_flag == 1:
        role = 'Instructor'
    else:
        role = 'Learner'

    return role

import pwd, grp, shutil
from ldap3 import Server, Connection, ALL
def create_home_hook(spawner, auth_state):

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, auth_stae_hook.\n")

    # if authentication information has been received safely.
    if auth_state:
        moodle_username = auth_state['ext_user_username']
        homePath = home_directory_root + '/' + moodle_username
        univserver = Server(global_ldap_server, get_info=ALL)
        if len(global_ldap_password) >= 5:
            univconn = Connection(univserver, password=global_ldap_password)
        else:
            univconn = Connection(univserver)
        conn_result = univconn.bind()
        # if connection to university ldap server failed.
        if not conn_result:
            sys.stderr.write("Cannot connect to ldap server in yuniversity.\n")
            return
        # if connection to university ldap server succeeded.
        else:
            if c.JupyterHub.log_level < 30:
                sys.stderr.write("Connect to ldap server in yuniversity.\n")
            search_result = univconn.search('uid=' + moodle_username + ',' + global_ldap_base_dn, '(objectclass=*)', attributes=['uidNumber','gidNumber','homeDirectory'])
            # when user is not a staff/student in university.
            if not search_result:
                sys.stderr.write("Error: User [" + moodle_username + "] does not exist in university ldap.\n")
                return
            # when user is a staff/student in university.
            else:
                # get properies for user.
                uidNumber = univconn.entries[0]['uidNumber'].value
                gidNumber = univconn.entries[0]['gidNumber'].value
                homeDirectory = univconn.entries[0]['homeDirectory'].value
                if c.JupyterHub.log_level < 30:
                    sys.stderr.write("uidNumber = " + str(uidNumber) + "\n")
                    sys.stderr.write("gidNumber = " + str(gidNumber) + "\n")
                    sys.stderr.write("homeDirectory = " + homeDirectory + "\n")
                # set group name and shell.

                if c.JupyterHub.log_level < 30:
                    if gidNumber == uidNumber:
                        sys.stderr.write("uidNumber == gidNumber.\n")
                    if homeDirectory.startswith('/st'):
                        sys.stderr.write("home directory is students.\n")
                    else:
                        sys.stderr.write("home directory is teachers.\n")

                if gidNumber == uidNumber and not homeDirectory.startswith('/st'):
                    if c.JupyterHub.log_level < 30:
                        sys.stderr.write("user = teachers.\n")
                    gidNumber = int(jupyterhub_groupid_teachers)
                    loginShell = '/bin/bash'
                else:
                    if c.JupyterHub.log_level < 30:
                        sys.stderr.write("user = students.\n")
                    gidNumber = int(jupyterhub_groupid_students)
                    loginShell = '/sbin/nologin'
                univconn.unbind()

                # If the user does not belong to our university currently.
                if not uidNumber:
                    if c.JupyterHub.log_level < 30:
                        sys.stderr.write("Error: User [" + moodle_username +"] does not belong to our university currently.\n")
                    return
                # If the user currently belongs our university.
                else:
                    localserver = Server(c.UniversitySwarmSpawner.ldap_server, get_info=ALL)
                    localconn = Connection(localserver, c.UniversitySwarmSpawner.ldap_manager_dn, password=c.UniversitySwarmSpawner.ldap_password, read_only=False)
                    conn_result = localconn.bind()
                    # if connection to local ldap server succeeded.
                    if not conn_result:
                        sys.stderr.write("Error: Cannot connect to local ldap server.\n")
                        return
                    else:
                        if c.JupyterHub.log_level < 30:
                            sys.stderr.write("Connect to local ldap server.\n")
                        search_result = localconn.search('uid=' + moodle_username + ',' + c.UniversitySwarmSpawner.ldap_base_dn, '(objectClass=*)')
                        add_home_flag = False
                        # The user is already registered in local ldap server.
                        if search_result:
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write("User (" +  moodle_username + ") already exists in local ldap.\n")
                            add_home_flag = True
                        else:
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write("User (" +  moodle_username + ") does not exists.\n")
                            email = moodle_username + "@" + email_domain
                            randomPass = pass_gen(12)
                            add_result = localconn.add('uid=' + moodle_username + ',' + c.UniversitySwarmSpawner.ldap_base_dn, ['posixAccount','inetOrgPerson'], {'uid':moodle_username,'cn':moodle_username,'sn':moodle_username,'uidNumber':uidNumber,'gidNumber':gidNumber,'homeDirectory':homePath,'loginShell':loginShell,'userPassword':randomPass,'mail': email})
                            if add_result:
                                add_home_flag = True
                                if c.JupyterHub.log_level < 30:
                                    sys.stderr.write("User (" + moodle_username + ") has been registered to ldap server.\n")
                            else:
                                sys.stderr.write("Error: Could not register new user to ldap server.\n")
                                return
                        localconn.unbind()

                        # System must create user's home directory.
                        if add_home_flag and not os.path.isdir(homePath) and not os.path.isfile(homePath):
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write("Try to create " + homePath + ".\n")
                            copyDirectory(skelton_directory, homePath)
                            if os.path.isdir(homePath):
                                if c.JupyterHub.log_level < 30:
                                    sys.stderr.write("Try to set owner premission.\n")
                                changeOwner(homePath, uidNumber, gidNumber)
                        else:
                            if c.JupyterHub.log_level < 30:
                                sys.stderr.write(homePath + " already exists.\n")

                    # Set environment variables.
                    set_user_environment_variables(spawner, auth_state, moodle_username, uidNumber, gidNumber)

                    # Create userdata for subject.
                    mount_volumes = create_userdata(spawner, auth_state, moodle_username)

                    if type(mount_volumes) == list and len(mount_volumes) != 0:
                        if c.JupyterHub.log_level < 30:
                            sys.stderr.write("new mount_volumes = " + str(mount_volumes) + "\n")
                        spawner.extra_container_spec['mounts'] = mount_volumes
                        spawner.extra_container_spec['user'] = '0'

                    role = get_user_role(auth_state)

                    spawner.environment = { 'MOODLECOURSE': auth_state['context_label'], 'COURSEROLE': role, 'MPLCONFIGDIR': homePath + '/.cache/matplotlib' , 'TZ': 'Asia/Tokyo', 'GRANT_SUDO': 'yes', 'HOME': homePath, 'PWD': homePath, 'PATH': homePath + '/.local/bin:' + homePath + '/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin' }

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("auth_state_hook finished.\n")

c.UniversitySwarmSpawner.auth_state_hook = create_home_hook

import os, shutil
def create_dir_hook(spawner):
    username = spawner.user.name  # get the username

    if c.JupyterHub.log_level < 30:
        sys.stderr.write("Hello, " + username + ", pre_spawn_hook.\n")

    spawner.cmd = [ '/usr/local/bin/start-singleuser.sh' ]
    spawner.args = ['--allow-root', '--user=' + username]

    spawner.image_homedir_format_string = home_directory_root + '/' + username

    if c.JupyterHub.log_level < 30:
        sys.stderr.write(str(spawner.get_state()) + "\n")
        sys.stderr.write("Finish pre_spawn_hook.\n")

c.UniversitySwarmSpawner.pre_spawn_hook = create_dir_hook

