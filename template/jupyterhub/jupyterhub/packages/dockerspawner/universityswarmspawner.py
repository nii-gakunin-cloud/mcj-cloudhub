"""
A Spawner for JupyterHub that runs each user's server in a separate docker service
"""
import asyncio
from pprint import pformat
from textwrap import dedent

from traitlets import Bool
from traitlets import Integer
from traitlets import Unicode

from docker.errors import APIError
from docker.types import ContainerSpec
from docker.types import DriverConfig
from docker.types import EndpointSpec
from docker.types import Mount
from docker.types import Placement
from docker.types import Resources
from docker.types import TaskTemplate
from traitlets import default
from traitlets import Dict
from traitlets import Unicode

from ldap3 import Server
from ldap3 import Connection
from ldap3 import ALL

import sys

from .dockerspawner import DockerSpawner

class UniversitySwarmSpawner(DockerSpawner):
    """A Spawner for JupyterHub that runs each user's server in a separate docker service"""

    object_type = "service"
    object_id_key = "ID"

    @default("pull_policy")
    def _default_pull_policy(self):
        # pre-pulling doesn't usually make sense on swarm
        # unless it's a single-node cluster, so skip it by efault
        return "skip"

    @property
    def service_id(self):
        """alias for object_id"""
        return self.object_id

    @property
    def service_name(self):
        """alias for object_name"""
        return self.object_name

    @default("network_name")
    def _default_network_name(self):
        # no default network for swarm
        # use internal networking by default
        return ""

    extra_resources_spec = Dict(
        config=True,
        help="""
        Keyword arguments to pass to the Resources spec
        """,
    )

    extra_container_spec = Dict(
        config=True,
        help="""
        Keyword arguments to pass to the ContainerSpec constructor
        """,
    )

    extra_placement_spec = Dict(
        config=True,
        help="""
        Keyword arguments to pass to the Placement constructor
        """,
    )

    extra_task_spec = Dict(
        config=True,
        help="""
        Keyword arguments to pass to the TaskTemplate constructor
        """,
    )

    extra_endpoint_spec = Dict(
        config=True,
        help="""
        Keyword arguments to pass to the Endpoint constructor
        """,
    )

    volume_driver = Unicode(
        "",
        config=True,
        help=dedent(
            """
            Use this driver for mounting the notebook volumes.
            Note that this driver must support multiple hosts in order for it to work across the swarm.
            For a list of possible drivers, see https://docs.docker.com/engine/extend/legacy_plugins/#volume-plugins
            """
        ),
    )

    volume_driver_options = Dict(
        config=True,
        help=dedent(
            """
            Configuration options for the multi-host volume driver.
            """
        ),
    )

    # container-removal cannot be disabled for services
    remove = True

    @property
    def mount_driver_config(self):
        if self.volume_driver:
            return DriverConfig(
                name=self.volume_driver, options=self.volume_driver_options or None
            )
        return None

    @property
    def mounts(self):
        if len(self.volume_binds):
            driver = self.mount_driver_config
            return [
                Mount(
                    target=vol["bind"],
                    source=host_loc,
                    type="bind",
                    read_only=vol["mode"] == "ro",
                    driver_config=driver,
                )
                for host_loc, vol in self.volume_binds.items()
            ]

        else:
            return []

#    host_homedir_format_string = Unicode(
#        "/home/{username}",
#        config=True,
#        help=dedent(
#            """
#            Format string for the path to the user's home directory on the host.
#            The format string should include a `username` variable, which will
#            be formatted with the user's username.
#
#            If the string is empty or `None`, the user's home directory will
#            be looked up via the `pwd` database.
#            """
#        ),
#    )

#    image_homedir_format_string = Unicode(
#        "/home/{username}",
#        config=True,
#        help=dedent(
#            """
#            Format string for the path to the user's home directory
#            inside the image.  The format string should include a
#            `username` variable, which will be formatted with the
#            user's username.
#            """
#        ),
#    )

#    run_as_root = Bool(
#        False,
#        config=True,
#        help="""Run the container as root
#
#        Relies on the image itself having handling of $NB_UID and $NB_GID
#        options to switch.
#
#        This was the default behavior prior to 0.12, but has become opt-in.
#        This enables images to nicely map usernames to userids inside the container.
#
#        .. versionadded:: 0.12
#        """,
#    )

    user_id = Integer(
        -1,
        config=True,
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
        config=True,
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

    homedir = Unicode(
        config=True,
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

#    @property
#    def host_homedir(self):
#        """
#        Path to the volume containing the user's home directory on the host.
#        Looked up from `pwd` if an empty format string or `None` has been specified.
#        """
#        if (
#            self.host_homedir_format_string is not None
#            and self.host_homedir_format_string != ""
#        ):
#            homedir = self.host_homedir_format_string.format(username=self.user.name)
#        else:
#            #import pwd
#
#            #homedir = pwd.getpwnam(self.user.name).pw_dir
#            homedir = ldap_get_home_dir()
#        return homedir

#    @property
#    def homedir(self):
#        """
#        Path to the user's home directory in the docker image.
#        """
#        return self.image_homedir_format_string.format(username=self.user.name)

    async def poll(self):
        """Check for my id in `docker ps`"""
        service = await self.get_task()
        if not service:
            self.log.warning("Service %s not found", self.service_name)
            return 0

        service_state = service["Status"]
        self.log.debug(
            "Service %s status: %s", self.service_id[:7], pformat(service_state)
        )

        if service_state["State"] in {"running", "starting", "pending", "preparing"}:
            return None

        else:
            return pformat(service_state)

    async def get_task(self):
        self.log.debug("Getting task of service '%s'", self.service_name)
        if await self.get_object() is None:
            return None

        try:
            tasks = await self.docker(
                "tasks",
                filters={"service": self.service_name, "desired-state": "running"},
            )
            if len(tasks) == 0:
                tasks = await self.docker(
                    "tasks",
                    filters={"service": self.service_name},
                )
                if len(tasks) == 0:
                    return None

            elif len(tasks) > 1:
                raise RuntimeError(
                    "Found more than one running notebook task for service '{}'".format(
                        self.service_name
                    )
                )

            task = tasks[0]
        except APIError as e:
            if e.response.status_code == 404:
                self.log.info("Task for service '%s' is gone", self.service_name)
                task = None
            else:
                raise

        return task

    def get_env(self):
        env = super(UniversitySwarmSpawner, self).get_env()
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

    async def create_object(self):
        """Start the single-user server in a docker service."""
        container_kwargs = dict(
            image=self.image,
            env=self.get_env(),
            args=(await self.get_command()),
            mounts=self.mounts,
        )
        container_kwargs.update(self.extra_container_spec)
        container_spec = ContainerSpec(**container_kwargs)

        resources_kwargs = dict(
            mem_limit=self.mem_limit,
            mem_reservation=self.mem_guarantee,
            cpu_limit=int(self.cpu_limit * 1e9) if self.cpu_limit else None,
            cpu_reservation=int(self.cpu_guarantee * 1e9)
            if self.cpu_guarantee
            else None,
        )
        resources_kwargs.update(self.extra_resources_spec)
        resources_spec = Resources(**resources_kwargs)

        placement_kwargs = dict(
            constraints=None,
            preferences=None,
            platforms=None,
        )
        placement_kwargs.update(self.extra_placement_spec)
        placement_spec = Placement(**placement_kwargs)

        task_kwargs = dict(
            container_spec=container_spec,
            resources=resources_spec,
            networks=[self.network_name] if self.network_name else [],
            placement=placement_spec,
        )
        task_kwargs.update(self.extra_task_spec)
        task_spec = TaskTemplate(**task_kwargs)

        endpoint_kwargs = {}
        if not self.use_internal_ip:
            endpoint_kwargs["ports"] = {None: (self.port, "tcp")}
        endpoint_kwargs.update(self.extra_endpoint_spec)
        endpoint_spec = EndpointSpec(**endpoint_kwargs)

        create_kwargs = dict(
            task_template=task_spec, endpoint_spec=endpoint_spec, name=self.service_name
        )
        create_kwargs.update(self.extra_create_kwargs)

        service = await self.docker("create_service", **create_kwargs)

        while True:
            tasks = await self.docker(
                "tasks",
                filters={"service": self.service_name},
            )
            if len(tasks) > 0:
                break
            await asyncio.sleep(1)

        return service

    @property
    def internal_hostname(self):
        return self.service_name

    async def remove_object(self):
        self.log.info("Removing %s %s", self.object_type, self.object_id)
        # remove the container, as well as any associated volumes
        await self.docker("remove_" + self.object_type, self.object_id)

    async def start_object(self):
        """Not actually starting anything

        but use this to wait for the container to be running.

        Spawner.start shouldn't return until the Spawner
        believes a server is *running* somewhere,
        not just requested.
        """

        dt = 1.0

        while True:
            service = await self.get_task()
            if not service:
                raise RuntimeError("Service %s not found" % self.service_name)

            status = service["Status"]
            state = status["State"].lower()
            self.log.debug("Service %s state: %s", self.service_id[:7], state)
            if state in {
                "new",
                "assigned",
                "accepted",
                "starting",
                "pending",
                "preparing",
                "ready",
                "rejected",
            }:
                # not ready yet, wait before checking again
                await asyncio.sleep(dt)
                # exponential backoff
                dt = min(dt * 1.5, 11)
            else:
                break
        if state != "running":
            raise RuntimeError(
                "Service %s not running: %s" % (self.service_name, pformat(status))
            )

    async def stop_object(self):
        """Nothing to do here

        There is no separate stop action for services
        """
        pass

    async def get_ip_and_port(self):
        """Queries Docker daemon for service's IP and port.

        If you are using network_mode=host, you will need to override
        this method as follows::

            async def get_ip_and_port(self):
                return self.host_ip, self.port

        You will need to make sure host_ip and port
        are correct, which depends on the route to the service
        and the port it opens.
        """
        if self.use_internal_hostname or self.use_internal_ip:
            ip = self.service_name
            port = self.port
        else:
            # discover published ip, port
            ip = self.host_ip
            service = await self.get_object()
            for port_config in service["Endpoint"]["Ports"]:
                if port_config.get("TargetPort") == self.port:
                    port = port_config["PublishedPort"]
                    break

            else:
                self.log.error(
                    "Couldn't find PublishedPort for %s in %s",
                    self.port,
                    service["Endpoint"]["Ports"],
                )
                raise RuntimeError(
                    "Couldn't identify port for service %s", self.service_name
                )

        return ip, port

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

    def _homedir_default(self):
        """
        Get group_id from pwd lookup by name

        If the authenticator stores group_id in the user state dict,
        this will never be called, which is necessary if
        the system users are not on the Hub system (i.e. Hub itself is in a container).
        """
        return self.ldap_get_homedir()

