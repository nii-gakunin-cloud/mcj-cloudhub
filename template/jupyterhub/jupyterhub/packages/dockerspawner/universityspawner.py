from textwrap import dedent

from traitlets import Bool
from traitlets import Integer
from traitlets import Unicode

from ldap3 import Server
from ldap3 import Connection
from ldap3 import ALL

from dockerspawner import DockerSpawner

import sys

class UniversitySpawner(DockerSpawner):

    host_homedir_format_string = Unicode(
        "/home/{username}",
        config=True,
        help=dedent(
            """
            Format string for the path to the user's home directory on the host.
            The format string should include a `username` variable, which will
            be formatted with the user's username.

            If the string is empty or `None`, the user's home directory will
            be looked up via the `pwd` database.
            """
        ),
    )

    image_homedir_format_string = Unicode(
        "/home/{username}",
        config=True,
        help=dedent(
            """
            Format string for the path to the user's home directory
            inside the image.  The format string should include a
            `username` variable, which will be formatted with the
            user's username.
            """
        ),
    )

    run_as_root = Bool(
        False,
        config=True,
        help="""Run the container as root

        Relies on the image itself having handling of $NB_UID and $NB_GID
        options to switch.

        This was the default behavior prior to 0.12, but has become opt-in.
        This enables images to nicely map usernames to userids inside the container.

        .. versionadded:: 0.12
        """,
    )

    user_id = Integer(
        -1,
        help=dedent(
            """
            If system users are being used, then we need to know their user id
            in order to mount the home directory.

            User IDs are looked up in two ways:

            1. stored in the state dict (authenticator can write here)
            2. lookup via pwd
            """
        ),
    )

    group_id = Integer(
        -1,
        help=dedent(
            """
            If system users are being used, then we need to know their group id
            in order to mount the home directory with correct group permissions.

            Group IDs are looked up in two ways:

            1. stored in the state dict (authenticator can write here)
            2. lookup via pwd
            """
        ),
    )

    ldap_server = Unicode(
        "127.0.0.1",
        config=True,
        help=("""Hostname or IP address of LDAP server"""),
    )

    ldap_base_dn = Unicode(
        "ou=People,dc=examople,dc=com",
        config=True,
        help=("""Base dn string to search LDAP information"""),
    )

    ldap_manager_dn = Unicode(
        "cn=Manager,dc=example,dc=com",
        config=True,
        help=("""Manager dn string to search LDAP information"""),
    )

    ldap_password = Unicode(
        "abcd1234",
        config=True,
        help=("""Password to connect to LDAP server as manager"""),
    )

    from ldap3 import Server, Connection, ALL
    def ldap_get_attribute(self, attrs = ['uid']):
        attr_value = None
        server = Server(self.ldap_server, get_info=ALL)
        if len(self.ldap_password) > 0 and self.ldap_password != "abcd1234":
            conn = Connection(server, self.ldap_manager_dn, self.ldap_password, read_only=True, auto_bind=True)
        else:
            conn = Connection(server, self.ldap_manager_dn, read_only=True, auto_bind=True)

        if conn:
            sys.stderr.write("Connect to local LDAP server.\n")
            result = conn.search('uid=' + self.user.name + ',' + self.ldap_base_dn, '(objectclass=*)', attributes=attrs)
            if result:
                response = conn.entries[0].entry_attributes_as_dict
            else:
                sys.stderr.write("Cannot find attribute: " + response + "\n")
            conn.unbind()
        else:
            sys.stderr.write("Could not connect to local LDAP server.\n")

        return response

    def ldap_get_userid(self):
        response = self.ldap_get_attribute(['uidNumber'])
        uidNumber = response['uidNumber']
        if uidNumber == None:
            return 0
        else:
            return uidNumber[0]

    def ldap_get_groupid(self):
        response = self.ldap_get_attribute(['gidNumber'])
        gidNumber = response['gidNumber']
        if gidNumber == None:
            return 0
        else:
            return gidNumber[0]

    def ldap_get_homedir(self):
        response= self.ldap_get_attribute(['homeDirectory'])
        homeDir = response['homeDirectory']
        if homeDir == None:
            return ""
        else:
            return homeDir[0]
    @property
    def host_homedir(self):
        """
        Path to the volume containing the user's home directory on the host.
        Looked up from `pwd` if an empty format string or `None` has been specified.
        """
        if (
            self.host_homedir_format_string is not None
            and self.host_homedir_format_string != ""
        ):
            homedir = self.host_homedir_format_string.format(username=self.user.name)
        else:
            #import pwd

            #homedir = pwd.getpwnam(self.user.name).pw_dir
            home_dir = ldap_get_home_dir()
            homedir = home_dir[0]
        return homedir

    @property
    def homedir(self):
        """
        Path to the user's home directory in the docker image.
        """
        return self.image_homedir_format_string.format(username=self.user.name)

    @property
    def volume_mount_points(self):
        """
        Volumes are declared in docker-py in two stages.  First, you declare
        all the locations where you're going to mount volumes when you call
        create_container.

        Returns a list of all the values in self.volumes or
        self.read_only_volumes.
        """
        mount_points = super(UniversitySpawner, self).volume_mount_points
        mount_points.append(self.homedir)
        return mount_points

    @property
    def volume_binds(self):
        """
        The second half of declaring a volume with docker-py happens when you
        actually call start().  The required format is a dict of dicts that
        looks like::

            {
                host_location: {'bind': container_location, 'ro': True}
            }
        """
        volumes = super(UniversitySpawner, self).volume_binds
        volumes[self.host_homedir] = {'bind': self.homedir, 'ro': False}
        return volumes

    def get_env(self):
        env = super(UniversitySpawner, self).get_env()
        # relies on NB_USER and NB_UID handling in jupyter/docker-stacks
        env.update(
            dict(
                USER=self.user.name,  # deprecated
                NB_USER=self.user.name,
                USER_ID=self.user_id,  # deprecated
                NB_UID=self.user_id,
                HOME=self.homedir,
            )
        )
        if self.group_id >= 0:
            env.update(NB_GID=self.group_id)
        return env

    def _user_id_default(self):
        """
        Get user_id from pwd lookup by name

        If the authenticator stores user_id in the user state dict,
        this will never be called, which is necessary if
        the system users are not on the Hub system (i.e. Hub itself is in a container).
        """
        # import pwd

        # return pwd.getpwnam(self.user.name).pw_uid
        return self.ldap_get_userid()

    def _group_id_default(self):
        """
        Get group_id from pwd lookup by name

        If the authenticator stores group_id in the user state dict,
        this will never be called, which is necessary if
        the system users are not on the Hub system (i.e. Hub itself is in a container).
        """
        # import pwd

        # return pwd.getpwnam(self.user.name).pw_gid
        return self.ldap_get_groupid()

    def load_state(self, state):
        super().load_state(state)
        if 'user_id' in state:
            self.user_id = state['user_id']
        if 'group_id' in state:
            self.group_id = state['group_id']

    def get_state(self):
        state = super().get_state()
        if self.user_id >= 0:
            state['user_id'] = self.user_id
        if self.group_id >= 0:
            state['group_id'] = self.group_id
        return state

    def start(self, *, image=None, extra_create_kwargs=None, extra_host_config=None):
        """start the single-user server in a docker container"""
        if image:
            self.log.warning("Specifying image via .start args is deprecated")
            self.image = image
        if extra_create_kwargs:
            self.log.warning(
                "Specifying extra_create_kwargs via .start args is deprecated"
            )
            self.extra_create_kwargs.update(extra_create_kwargs)
        if extra_host_config:
            self.log.warning(
                "Specifying extra_host_config via .start kwargs is deprecated"
            )
            self.extra_host_config.update(extra_host_config)

        self.extra_create_kwargs.setdefault('working_dir', self.homedir)
        if self.run_as_root:
            # systemuser images derived from Jupyter docker stacks
            # can start as root and 'become' $NB_UID with proper
            # name and everything.
            # relies on $NB_UID and $NB_USER env handling in those images
            # make this opt-in since without it, all users will run as root
            self.extra_create_kwargs.setdefault('user', '0')
        elif self.user_id >= 0:
            user_s = str(self.user_id)
            if self.group_id >= 0:
                user_s = f"{user_s}:{self.group_id}"
            self.extra_create_kwargs.setdefault('user', user_s)
        elif self.group_id >= 0:
            # group_id set, but user_id not set.
            # this doesn't make sense.
            self.log.warning(
                f"user_id for {self.user.name} not set, but group_id is {self.group_id}. This will have no effect."
            )

        return super(UniversitySpawner, self).start()

