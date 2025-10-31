import binascii
import logging
import os
import sys
from textwrap import dedent

from jinja2 import ChoiceLoader, FileSystemLoader
from jupyterhub._data import DATA_FILES_PATH
from jupyterhub.handlers.static import LogoHandler
from jupyterhub.log import CoroutineLogFormatter
from jupyterhub.services.auth import HubOAuthCallbackHandler
from jupyterhub.utils import url_path_join
from tornado import ioloop, web
from traitlets import Bool, Dict, Integer, List, Unicode, default
from traitlets.config import Application

from handlers import (
    TeacherToolsUpdateHandler,
    TeacherToolsViewHandler,
    TeacherToolsLogDBHandler,
)


class TeacherToolsService(Application):

    flags = Dict(
        {
            "generate-config": (
                {"TeacherToolsService": {"generate_config": True}},
                "Generate default config file",
            )
        }
    )

    aliases = {
        'port': 'TeacherToolsService.port',
        'lms-token-endpoint': 'TeacherToolsService.lms_token_endpoint',
        'lms-client-id': 'TeacherToolsService.lms_client_id',
        'homedir': 'TeacherToolsService.homedir',
    }

    hub_api_url = Unicode(
        os.environ.get("JUPYTERHUB_API_URL", "http://jupyterhub:8081/hub/api"),
        help="jupyterhub api url",
    ).tag(config=True)

    generate_config = Bool(
        False, help="Generate default config file"
    ).tag(config=True)

    config_file = Unicode(
        "teacher_tools_config.py", help="Config file to load"
    ).tag(config=True)

    service_prefix = Unicode(
        os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/services/teachertools/"),
        help="Service url prefix",
    ).tag(config=True)

    port = Integer(9999, help="Port this service will listen on"
                   ).tag(config=True)

    data_files_path = Unicode(DATA_FILES_PATH,
                              help="Location of JupyterHub data files")

    template_paths = List(
        help="Search paths for jinja templates, coming before default ones"
    ).tag(config=True)

    @default("template_paths")
    def _template_paths_default(self):
        return [
            os.path.join("/etc/jupyterhub/service-teachertools", "templates"),
            os.path.join(self.data_files_path, "templates"),
        ]

    logo_file = Unicode(
        "",
        help="Logo path, can be used to override JupyterHub one",
    ).tag(config=True)

    @default("logo_file")
    def _logo_file_default(self):
        return os.path.join(
            self.data_files_path, "static", "images", "jupyterhub-80.png"
        )

    fixed_message = Unicode(
        "",
        help=dedent(
            """Fixed message to show at the top of the page.

            A good use for this parameter would be a link to a more general
            live system status page or MOTD.
            """
        ).strip(),
    ).tag(config=True)

    cookie_secret_file = Unicode(
        "/srv/jupyterhub/jupyterhub_cookie_secret",
        help="File in which we store the cookie secret.",
    ).tag(config=True)

    lms_token_endpoint = Unicode(
        "",
        help=dedent(
            """
            LMS access token endpoint.
            """
        ).strip(),
        allow_none=False,
    ).tag(
        config=True,
    )

    lms_client_id = Unicode(
        "",
        help=dedent(
            """
            LMS client id.
            """
        ).strip(),
        allow_none=False,
    ).tag(
        config=True,
    )

    homedir = Unicode(
        "/home",
        help=dedent(
            """
            Root directory for user's home.
            """
        ).strip(),
        allow_none=False,
    ).tag(
        config=True,
    )

    _log_formatter_cls = CoroutineLogFormatter

    @default("log_datefmt")
    def _log_datefmt(self):
        return "%Y-%m-%d %H:%M:%S"

    @default("log_format")
    def _log_format(self):
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def initialize(self, argv=None):
        super().initialize(argv)

        if self.generate_config:
            print(self.generate_config_file())
            sys.exit(0)

        if self.config_file:
            self.load_config_file(self.config_file)

        base_path = self._template_paths_default()[0]
        if base_path not in self.template_paths:
            self.template_paths.append(base_path)
        loader = ChoiceLoader([
            FileSystemLoader([base_path]),
            FileSystemLoader(self.template_paths),
        ])

        with open(self.cookie_secret_file, "rb") as f:
            raw = f.read().strip()
        try:
            cookie_secret = binascii.a2b_hex(raw)
        except binascii.Error:
            cookie_secret = raw

        self.settings = {
            "cookie_secret": cookie_secret,
            "static_path": os.path.join(self.data_files_path, "static"),
            "static_url_prefix": url_path_join(self.service_prefix, "static/"),
            "log": self.log,
            "xsrf_cookies": True,
            'homedir': self.homedir,
            'hub_api_url': self.hub_api_url,
        }

        if "xsrf_cookie_kwargs" not in self.settings:
            # default: set xsrf cookie on service url
            self.settings["xsrf_cookie_kwargs"] = {
                "path": os.getenv("JUPYTERHUB_SERVICE_PREFIX",
                                  f"/services/{os.environ['JUPYTERHUB_SERVICE_NAME']}")}

        self.app = web.Application(
            [
                (
                    self.service_prefix, TeacherToolsViewHandler,
                    dict(loader=loader,
                         service_prefix=self.service_prefix,
                         fixed_message=self.fixed_message,
                         )
                ),
                (
                    self.service_prefix + r"api/ags/scores",
                    TeacherToolsUpdateHandler,
                    dict(lms_token_endpoint=self.lms_token_endpoint,
                         lms_client_id=self.lms_client_id,
                         )
                ),
                (
                    self.service_prefix + r"api/log_collect",
                    TeacherToolsLogDBHandler,
                ),
                (
                    self.service_prefix + r"oauth_callback",
                    HubOAuthCallbackHandler
                ),
                (
                    self.service_prefix + r"static/(.*)",
                    web.StaticFileHandler,
                    dict(path=self.settings["static_path"]),
                ),
                (
                    self.service_prefix + r"logo",
                    LogoHandler,
                    {"path": self.logo_file}
                ),
                (
                    r'.*', TeacherToolsViewHandler,
                    dict(loader=loader,
                         service_prefix=self.service_prefix,
                         fixed_message=self.fixed_message,
                         )
                ),
            ],
            **self.settings,
        )

    def init_logging(self):
        # This prevents double log messages because tornado use a root logger
        # that self.log is a child of. The logging module dipatches log
        # messages to a log and all of its ancenstors until propagate is set to
        # False.
        self.log.propagate = False

        # disable curl debug, which is TOO MUCH
        logging.getLogger("tornado.curl_httpclient").setLevel(
            max(self.log_level, logging.INFO)
        )

        for name in ("access", "application", "general"):
            # ensure all log statements identify the application they come from
            log = logging.getLogger(f"tornado.{name}")
            log.name = self.log.name

        # hook up tornado's and oauthlib's loggers to our own
        for name in ("tornado", "oauthlib"):
            logger = logging.getLogger(name)
            logger.propagate = True
            logger.parent = self.log
            logger.setLevel(self.log.level)

    def start(self):
        self.app.listen(self.port)
        ioloop.IOLoop.current().start()


def main():
    app = TeacherToolsService()
    app.initialize()
    app.start()


if __name__ == "__main__":
    main()
