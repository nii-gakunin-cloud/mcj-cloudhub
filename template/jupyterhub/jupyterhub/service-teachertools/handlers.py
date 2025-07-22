import datetime
from http import HTTPStatus
import json
import logging
import os
import requests

from jupyterhub.services.auth import HubOAuthenticated
from jupyterhub.utils import url_path_join
from jinja2 import Environment
from nbgrader.api import Gradebook, MissingEntry
from pydantic import ValidationError
from tornado import escape, web

from lti import get_lms_lti_token, confirm_key_exist
from models import LineItem, Score
from nbgrader_utils import get_course_assignments, get_grades, db_path, log2db
from utils import ldapClient


require_scopes = (
    'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
    'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly',
    'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
    'https://purl.imsglobal.org/spec/lti-ags/scope/score',
)
lms_token = None
private_key, _ = confirm_key_exist()


class TeacherToolsException(Exception):
    def __init__(self, arg=''):
        self.arg = arg


class TeacherToolsHandler(HubOAuthenticated, web.RequestHandler):
    def initialize(self):
        super().initialize()
        self.hub_api_url = self.settings["hub_api_url"]
        self.homedir = self.settings["homedir"]

    @property
    def log(self):
        return self.settings.get("log",
                                 logging.getLogger("tornado.application"))

    def get_user_info(self, user):
        headers = {"Authorization": f"token {os.environ['JUPYTERHUB_API_TOKEN']}"}
        url = f"{self.hub_api_url}/users/{user['name']}"
        r = requests.get(url, headers=headers)
        return r.json()

    def course_shortname(self, user, homedir='/home'):

        # 存在するコースかチェック（このユーザのhomeディレクトリ配下に存在）
        # auth_stateを確認
        user_info = self.get_user_info(user)
        if user_info.get('auth_state'):
            course_name = user_info['auth_state']['https://purl.imsglobal.org/spec/lti/claim/context']['label']
        else:
            course_name = user['groups'][0]
        course_dir = os.path.join(homedir, user['name'], 'nbgrader', course_name)
        if not os.path.isdir(course_dir):
            raise FileNotFoundError(f'Not found course directory: {course_dir}')
        return course_name


class TeacherToolsOutputHandler(TeacherToolsHandler):

    def initialize(self):
        super().initialize()

    def json_output(self, status_code=None, reason=None, output={}):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        if status_code:
            self.set_status(status_code, reason)
        if len(output) == 0:
            _output = {}
        else:
            _output = output
        self.write(json.dumps(_output, indent=1, sort_keys=True))


class TeacherToolsLogDBHandler(TeacherToolsOutputHandler):
    """Update log db"""

    _token_authenticated = True

    def initialize(self):
        super().initialize()

    @web.authenticated
    async def post(self):
        user = self.get_current_user()
        self.json_data = escape.json_decode(self.request.body)
        try:
            # required params
            course = self.json_data.get('course')
        except KeyError as e:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST, f"Missing required paramater: {e}"
            )

        dt_from = self.json_data.get('from')
        dt_to = self.json_data.get('to')
        assignment = self.json_data.get('assignment')
        opt = {}
        if dt_from is not None:
            opt['dt_from'] = datetime.datetime.fromisoformat(dt_from)
        if dt_to is not None:
            opt['dt_to'] = datetime.datetime.fromisoformat(dt_to)
        if assignment is not None:
            opt['assignment'] = assignment
        try:
            db_path = log2db(course, user["name"], self.homedir, **opt)
        except FileNotFoundError as e:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                f"directory not found: {os.path.join('~', str(e))}"
            )

        res = dict()
        res['db_path'] = db_path
        res['dt_from'] = opt['dt_from'].isoformat() if 'dt_from' in opt else ""
        res['dt_to'] = opt['dt_to'].isoformat() if 'dt_to' in opt else ""
        res['assignment'] = opt.get('assignment')
        self.json_output(output=res)


class TeacherToolsUpdateHandler(TeacherToolsOutputHandler):
    """POST grades to LMS with AGS"""

    hub_users = []
    allow_admin = True

    def initialize(self, lms_token_endpoint, lms_client_id):
        super().initialize()
        self.lms_token_endpoint = lms_token_endpoint
        self.lms_client_id = lms_client_id

    def get_uid(self, username):
        ldap_manager_dn = f'cn={os.getenv("LDAP_ADMIN", "Manager")},'\
                        'dc=jupyterhub,dc=server,dc=sample,dc=jp'
        ldapconn = ldapClient(os.environ['LDAP_SERVER'],
                              ldap_manager_dn,
                              os.environ['LDAP_PASSWORD'])
        search_result = ldapconn.search_user(username, ['uidNumber'])
        return int(search_result[0].uidNumber.value) if search_result is not None else None

    def _request_lms(self, url, headers, method="GET", params=None, data=None, timeout=10):
        global lms_token
        if lms_token is None:
            lms_token = get_lms_lti_token(
                                require_scopes,
                                os.environ['JUPYTERHUB_BASE_URL'],
                                private_key,
                                self.lms_token_endpoint,
                                self.lms_client_id)
        _headers = headers.copy()
        _headers['Authorization'] = f'Bearer {lms_token}'

        response = requests.request(
            method,
            url,
            params=params,
            data=data,
            headers=_headers,
            timeout=timeout
        )
        if HTTPStatus.UNAUTHORIZED == response.status_code:
            # service用tokenが有効期限切れになっている場合再発行
            lms_token = get_lms_lti_token(require_scopes,
                                            os.environ['JUPYTERHUB_BASE_URL'],
                                            private_key,
                                            self.lms_token_endpoint,
                                            self.lms_client_id)
            self.log.warning("LMS access token expired and recreated.")
            # 再度リクエスト
            _headers['Authorization'] = f'Bearer {lms_token}'
            response = requests.request(
                method,
                url,
                params=params,
                data=data,
                headers=_headers,
                timeout=timeout
            )
        if HTTPStatus.UNAUTHORIZED == response.status_code:
            # service用tokenの再発行に失敗
            self.log.error(f"LMS access token expired and refresh failed. msg: {response.text}")
            raise TeacherToolsException(response.text)
        return response

    def get_lineitem_id_from_assignment(self, url, assignment: str):
        """
        未登録のlineitemの場合、Noneが返る
        """
        headers = {'Accept': 'application/vnd.ims.lis.v2.lineitemcontainer+json'}
        response = self._request_lms(url, headers)
        for lineitem in response.json():
            if lineitem['label'] == assignment:
                lineitem_id = lineitem['id']
                return lineitem_id

    def register_lineitem(self, url: str, lineitem: LineItem):
        headers = {'Accept': 'application/vnd.ims.lis.v2.lineitem+json',
                   "Content-Type": "application/vnd.ims.lis.v2.lineitem+json"}
        response = self._request_lms(url, headers, method="POST",
                                     data=lineitem.model_dump_json())
        return response

    def register_score(self, url: str, score: Score):
        headers = {'Accept': 'application/vnd.ims.lis.v1.score+json',
                   'Content-Type': 'application/vnd.ims.lis.v1.score+json',}
        response = self._request_lms(url, headers, method="POST",
                                     data=score.model_dump_json())
        return response

    @web.authenticated
    async def post(self):
        user = self.get_current_user()
        self.json_data = escape.json_decode(self.request.body)
        global lms_token
        try:
            assignment_name = self.json_data['assignment']
        except KeyError as e:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST, f"Missing required paramater: {e}"
            )

        # 教師用ディレクトリがホームディレクトリ配下に存在するか？
        try:
            course_id = self.course_shortname(user, self.homedir)
        except FileNotFoundError as e:
            raise web.HTTPError(
                HTTPStatus.NOT_FOUND, e
            )

        user_info = self.get_user_info(user)

        # 教師roleが割り当てられているか？
        if f"instructor-{course_id}" not in user_info['roles']:
            raise web.HTTPError(
                HTTPStatus.FORBIDDEN, f"User is not teacher for course {user['groups'][0]}"
            )

        # TODO ログイン中にJupyterhub再起動など行うと、auth_state情報が失われるためエラーになる
        if user_info.get('auth_state') is None:
            raise web.HTTPError(
                HTTPStatus.UNAUTHORIZED, "User may be logged out. Login required."
            )

        ags_url = user_info['auth_state']["https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"]['lineitems']
        from urllib.parse import urlsplit, urlunsplit

        # Check assignment info exists in nbgrader db
        gb_dir = db_path(user['name'], course_id, self.homedir)
        with Gradebook(f'sqlite:///{gb_dir}') as gb:
            try:
                assignment = gb.find_assignment(assignment_name)
            except MissingEntry:
                raise web.HTTPError(
                    HTTPStatus.NOT_FOUND, f"Not found assignment in db: {assignment_name}"
                )

        parts = urlsplit(ags_url)
        ags_url_base = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        ags_url_query = parts.query

        # Search lineitem(column)
        lineitem_id = self.get_lineitem_id_from_assignment(
            f'{ags_url_base}?{ags_url_query}', assignment.name)

        # Add lineitem(column)
        if lineitem_id is None:
            try:
                lineitem = LineItem(
                    label=assignment.name,
                    scoreMaximum=assignment.max_score,
                )
            except ValidationError as e:
                raise web.HTTPError(
                    HTTPStatus.NOT_ACCEPTABLE, e.errors()
                )

            response = self.register_lineitem(f'{ags_url_base}?{ags_url_query}', lineitem)

            if HTTPStatus.CREATED != response.status_code:
                raise web.HTTPError(
                    response.status_code, "Lineitem register failed"
                )

            # http://sample.com/mod/lti/services.php/6/lineitems/28/lineitem?type_id=1 などが返る
            lineitem_id = response.json()['id']

        parts = urlsplit(lineitem_id)
        ags_url_base = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        ags_url_query = parts.query
        grades = get_grades(course_id,
                            assignment.name,
                            user['name'],
                            homedir=self.homedir)

        for grade in grades:
            uid = self.get_uid(grade['student'])

            if uid is None:
                self.log.warning(f'User {grade["student"]} skipped because user info is not exist (maybe the user never logged in).')
                continue

            # TODO uidのprefix指定オプション対応(現状固定で、moodleでのid+1000がuid)
            try:
                score = Score(
                    userId=uid - 1000,
                    scoreGiven=grade['score'],
                    scoreMaximum=grade['max_score'],
                )
            except ValidationError as e:
                raise web.HTTPError(
                    HTTPStatus.NOT_ACCEPTABLE, e.errors()
                )

            response = self.register_score(
                f'{ags_url_base}/scores?{ags_url_query}',
                score)
            if not (200 <= response.status_code < 300):
                raise web.HTTPError(
                    response.status_code, "Score register failed"
                )
        self.json_output()


class TeacherToolsViewHandler(TeacherToolsHandler):
    """Return Top page"""

    def initialize(self, loader, service_prefix, fixed_message=None):
        super().initialize()
        self.loader = loader
        self.service_prefix = service_prefix
        self.env = Environment(loader=self.loader)
        self.template = self.env.get_template("index.html")
        self.fixed_message = fixed_message

    @web.authenticated
    def get(self):
        prefix = self.hub_auth.hub_prefix
        logout_url = url_path_join(prefix, "logout")
        user = self.get_current_user()
        post_url = url_path_join(self.service_prefix, "api/ags/scores")

        course_name = self.course_shortname(user, self.homedir)
        assignments = get_course_assignments(user['name'],
                                             course_name,
                                             self.homedir)
        announce = self.fixed_message if self.fixed_message else None
        self.write(
            self.template.render(user=user,
                                 announcement=announce,
                                 static_url=self.static_url,
                                 logout_url=logout_url,
                                 post_url=post_url,
                                 base_url=prefix,
                                 xsrf_token=self.xsrf_token.decode('utf8'),
                                 admin_access=user['admin'],
                                 no_spawner_check=True,
                                 course_name=course_name,
                                 assignments=assignments,
                                 parsed_scopes=user.get('scopes') or [],
                                 )
        )

