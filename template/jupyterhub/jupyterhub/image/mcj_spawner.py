"""
A Spawner for JupyterHub that runs each user's server in a separate docker service
"""
import asyncio
from pprint import pformat
from textwrap import dedent

from docker.errors import APIError
from docker.types import (
    ContainerSpec,
    DriverConfig,
    EndpointSpec,
    Mount,
    Placement,
    Resources,
    TaskTemplate)
from ldap3 import (
    Server,
    Connection,
    ALL)
from traitlets import (
    default,
    Dict,
    Unicode,
    Integer)

from dockerspawner import DockerSpawner


DOCKER_SERVICE_STATES_NO_LOG = {
    "running", "starting", "pending", "preparing"}
DOCKER_STATE_DESIRED = "running"


class SysUserSwarmSpawner(DockerSpawner):
    """A Spawner for JupyterHub that runs each user's server in a separate docker service"""

    object_type = "service"
    object_id_key = "ID"

    @default("pull_policy")
    def _default_pull_policy(self):
        # pre-pulling doesn't usually make sense on swarm
        # unless it's a single-node cluster, so skip it by default
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

    def _args_default(self):
        """
        Get args for run the container
        """
        return ['--allow-root']

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

    user_id = Integer(
        -1,
        config=True,
        help=dedent(
            """
            If system users are being used, then we need to know their user id
            in order to mount the home directory.

            User must be specified.
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
 
            Group ID must be specified.
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

            1. specify this param
            2. lookup via ldap
            """
        ),
    )

    ldap_server = Unicode(
        "127.0.0.1",
        config=True,
        help=("""Hostname or IP address of LDAP server"""),
    )

    ldap_base_dn = Unicode(
        "ou=People,dc=example,dc=com",
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

    login_user_name = Unicode(
        "",
        config=True,
        help=("""Login user name for single-user server"""),
    )

    def ldap_get_attribute(self, attrs=['uid']):
        server = Server(self.ldap_server, get_info=ALL)
        conn = Connection(server,
                          self.ldap_manager_dn,
                          self.ldap_password,
                          read_only=True,
                          auto_bind=True,
                          raise_exceptions=True)
        response = None
        if conn:
            self.log.info("Connect to local LDAP server.")
            result = conn.search(self.ldap_base_dn,
                                 f'(uidNumber={self.user_id})',
                                 attributes=attrs,
                                 )

            if result:
                response = conn.entries[0].entry_attributes_as_dict
            else:
                self.log.error(f"Cannot find attribute: {attrs}")
            conn.unbind()
        else:
            self.log.error("Could not connect to local LDAP server.")

        return response

    async def poll(self):
        """Check for my id in `docker ps`"""
        service = await self.get_task()
        if not service:
            self.log.warning("Service %s not found", self.service_name)
            return 0

        service_state = service["Status"]
        self.log.debug(
            "Service %s status: %s",
            self.service_id[:7],
            pformat(service_state)
        )

        if service_state["State"] in DOCKER_SERVICE_STATES_NO_LOG:
            return None

        return pformat(service_state)

    async def get_task(self):
        self.log.debug("Getting task of service '%s'", self.service_name)
        if await self.get_object() is None:
            return None

        try:
            tasks = await self.docker(
                "tasks",
                filters={"service": self.service_name,
                         "desired-state": DOCKER_STATE_DESIRED},
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
                self.log.info("Task for service '%s' is gone",
                              self.service_name)
                task = None
            else:
                raise

        return task

    def get_env(self):
        env = super(SysUserSwarmSpawner, self).get_env()
        env.update(
            dict(
                NB_USER=self.login_user_name if self.login_user_name else self.user.name,
                NB_UID=self.user_id,
                NB_GID=self.group_id,
                HOME=self.homedir,
            )
        )

        if self.user_options.get('uid_number'):
            username = self.login_user_name if self.login_user_name else self.user.name
            env.update(
                dict(
                    NB_UID=self.user_options['uid_number'],
                    NB_GID=self.user_options['gid_number'],
                    MOODLECOURSE=self.user_options['gid_number'],
                    COURSEROLE=self.user_options['COURSEROLE'],
                    TEACHER_GID=self.user_options['TEACHER_GID'],
                    STUDENT_GID=self.user_options['STUDENT_GID'],
                    PATH=f'/{username}/testuser01/.local/bin:/jupyter/{username}/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin',
                )
            )
            self.extra_container_spec['mounts'] = [
                {'type': 'bind',
                 'source': f'/jupyter/{username}',
                 'target': f'/home/{username}',
                 'ReadOnly': False},
                {'type': 'bind',
                 'source': '/exchange/nbgrader/exchange/mcjh',
                 'target': '/jupytershare/nbgrader/exchange/mcjh',
                 'ReadOnly': False}]

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
