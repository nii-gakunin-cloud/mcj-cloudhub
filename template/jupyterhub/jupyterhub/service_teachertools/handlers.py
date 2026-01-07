from datetime import datetime, timezone
import glob
from http import HTTPStatus
import json
import logging
import os
import re
import requests

from jupyterhub.services.auth import HubAuthenticated, HubOAuthenticated
from jupyterhub.utils import url_path_join
from jinja2 import Environment
from nbgrader.api import Gradebook, MissingEntry
from pydantic import ValidationError
from tornado import escape, web
from sqlmodel import Session, create_engine

from lti import get_lms_lti_token, confirm_key_exist
from models import LineItem, Score, init_db, StudentCreate, CellCreate, LogCreate
import crud
from nbgrader_utils import (get_course_assignments, get_grades,
                            db_path, get_course_students)
from utils import ldapClient


require_scopes = (
    'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
    'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly',
    'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
    'https://purl.imsglobal.org/spec/lti-ags/scope/score',
)
course_info_key = 'https://purl.imsglobal.org/spec/lti/claim/context'
lms_token = None
private_key, _ = confirm_key_exist()


DEFAULT_DT_FROM = datetime(1970, 1, 1, tzinfo=timezone.utc)


def remove_uuid_branch(uuid_string):
    parts = uuid_string.split('-')
    if len(parts) > 5:
        return '-'.join(parts[:5])
    return uuid_string


def jst2datetime(dt: str) -> datetime:
    """JSTのタイムスタンプをdatetime型に変換する

    LC_wrapperに登録されているタイムスタンプ型をタイムゾーン情報を持つdatetime型に変換する。

    :param dt: JSTタイムスタンプ（'%Y-%m-%d %H:%M:%S (JST)'）
    :type dt: string
    :returns: datetime
    :rtype: datetime

    >>> jst2datetime("2024-10-18 19:32:54(JST)")
    datetime.datetime(2024, 10, 18, 19, 32, 54, tzinfo=timezone(datetime.timedelta(seconds=32400)))
    """
    converted_dt = datetime.strptime(
        dt.replace('(JST)', ' +0900'), '%Y-%m-%d %H:%M:%S %z')
    return converted_dt


def get_cell_info(cells: list) -> list:
    """.ipynb形式のノートブックのセルデータを整理する

    cellのタイプが'code'であるセルのみを抽出する。
    cellのタイプが'markdown'であるセルは、先頭が`#`始まりの場合、見出しセルとみなして
    章番号を取得する。
    LC_wrapperで出力されるログを想定している。

    :param cells: ノートブックのセル情報のリスト
    :type cells: list

    >>> get_cell_info([
    ...     {
    ...         "cell_type": "markdown",
    ...         "id": "5f44c941",
    ...         "metadata": {
    ...             "lc_cell_meme": {
    ...                 "current": "cd9eaa0a-90e4-11ef-aad1-02420a010038",
    ...                 "next": "cd9eaadc-90e4-11ef-aad1-02420a010038",
    ...                 "previous": None
    ...             }
    ...         },
    ...         "source": [
    ...           "# this is markdown cell title"
    ...         ]
    ...     },
    ...     {
    ...         "cell_type": "code",
    ...         "execution_count": 1,
    ...         "id": "4855ae0b",
    ...         "metadata": {
    ...             "lc_cell_meme": {
    ...                 "current": "cd9eab9a-90e4-11ef-aad1-02420a010038",
    ...                 "execution_end_time": "2024-10-23T02:15:28.653396Z",
    ...                 "next": "cd9eac26-90e4-11ef-aad1-02420a010038",
    ...                 "previous": "cd9eaadc-90e4-11ef-aad1-02420a010038"
    ...             }
    ...         },
    ...         "outputs": [],
    ...         "source": [
    ...           "this is code cell"
    ...         ]
    ...     }
    ... ])
    [{'cell_id': 'cd9eab9a-90e4-11ef-aad1-02420a010038', 'jupyter_cell_id': '4855ae0b', 'section': '1'}]
    """

    class __NBSection():
        """Markdownの章立てを把握するためのクラス

        最新の章番号をListで持つ。1.1.1 の場合、[1, 1, 1]。
        章番号をインクリメントするindexを指定してインクリメントしていく。
        """
        current = []

        def count_hashes(self, s) -> int:
            """先頭の`#`の数を返す
            :param s: 先頭の`#`の数をカウントしたい文字列
            :type s: string
            :returns: 先頭の`#`の数
            :rtype: int

            >>> count_hashes('## This is Second Section')
            2
            """
            match = re.match(r'#+', s)
            return len(match.group(0)) if match else 0

        def increment_section(self, level: int):
            """章番号をインクリメントする

            :param level: インクリメントする章の階層（`#`の数を指定する）
            :type level: int
            """
            if len(self.current) <= level:
                diff = [0 for i in range(level - len(self.current))]
                self.current.extend(diff)
            else:
                self.current[level:] = []
            self.current[level-1] += 1

        def get_current_section(self):
            """現在の章番号を返す
            現在の章番号を文字列で返す。
            :returns: 章番号をドット区切りにした文字列。ex. "1.1.1"
            :rtype: str
            """
            return ".".join([str(_) for _ in self.current.copy()])

    cell_ids = list()
    cell_id_key = 'lc_cell_meme'
    sections = __NBSection()
    for cell in cells:
        if cell['cell_type'] == 'code':
            cell_id = cell['metadata'].get(cell_id_key)
            if cell_id is None:
                continue
            nbgrader_info = cell['metadata'].get('nbgrader')
            cell_ids.append(dict(cell_id=cell_id['current'],
                                 jupyter_cell_id=cell['id'],
                                 section=sections.get_current_section(),
                                 nbgrader_cell_id=cell['metadata']['nbgrader']['grade_id'] if nbgrader_info is not None else None
                                 ))
        elif cell['cell_type'] == 'markdown':
            if len(cell['source']) == 0:
                continue
            # 章番号があればインクリメント
            level = sections.count_hashes(cell['source'][0])
            if level > 0:
                sections.increment_section(level)
        else:
            continue
    return cell_ids


def update_or_create_log_student(db_url: str, students: list):
    """コースの学生一覧をDBに登録する
    Delete&Insertを行う。LMSから削除された学生はログからも削除される。

    :param db_path: DBファイルのパス
    :type db_path: string
    :param students: 学生名リスト e.g. ['student01', 'student02',]
    :type students: list
    """
    if len(students) == 0:
        return
    engine = create_engine(db_url)
    data = [StudentCreate(id=student_id) for student_id in students]
    with Session(engine) as session:
        crud.create_students(session=session, students_create=data,
                             skip_exists=True)


def update_or_create_cell_id(db_url: str, notebook_name: str,
                             assignment: str, cell_infos: list):
    """コースの課題に設定されているノートブックから、コードセルのID一覧をDBに登録する

    :param db_path: DBファイルのパス
    :type db_path: string
    :param notebook_name: ノートブック名
    :type notebook_name: string
    :param assignment: 課題名
    :type assignment: string
    :param cell_infos: セル情報リスト e.g. [{'cell_id': 'cell01', 'section': '1.1.1'}]
    :type cell_infos: list
    """

    if len(cell_infos) == 0:
        return
    engine = create_engine(db_url)
    # ノートブックを複製利用した場合など、uuidに枝番が付く場合があるが、ここでは切り捨てない
    # ただし、出力されるログディレクトリ名では枝番が付かないので注意する
    data = [CellCreate(id=cell_info['cell_id'],
                       assignment=assignment,
                       section=cell_info['section'],
                       notebook_name=notebook_name,
                       jupyter_cell_id=cell_info['jupyter_cell_id'],
                       nbgrader_cell_id=cell_info['nbgrader_cell_id']) for cell_info in cell_infos]
    with Session(engine) as session:
        # TODO skip_existsではなく、skip="update"/"ignore"/"error" nbgrader_cell_idなど変更OKなものがあるため。
        # 現状、nbgraderでは提出がある課題は再generate出来ないので、cell定義が変更されることは無い。
        crud.create_cells(session=session, cells_create=data, skip_exists=True)
        session.commit()


def update_or_create_log(db_url: str,  notebook_name: str,
                         assignment: str, user_id: str,
                         cell_id: str, logs: list[dict], dt_from: datetime,
                         dt_to: datetime):
    """学生の実行履歴情報をDBに登録する
    ログの実行完了時刻が指定日時内でない場合は登録しない。

    :param db_url: DBファイルのパス
    :type db_url: string
    :param notebook_name: ノートブック名
    :type notebook_name: string
    :param assignment: 課題名
    :type assignment: string
    :param cell_infos: セル情報リスト e.g. [{'cell_id': 'cell01', 'section': '1.1.1'}]
    :type cell_infos: list
    :param dt_from: 対象データの始点日時
    :type dt_from: datetime
    :param dt_to: 対象データの終点日時
    :type dt_to: datetime
    """

    if len(logs) == 0:
        return

    values = list()

    for i, log in enumerate(logs):

        # TODO: そもそも取得しないよう修正する
        if jst2datetime(log['end']) > dt_to or dt_from > jst2datetime(log['end']):
            continue

        values.append(LogCreate(
            assignment=assignment,
            student_id=user_id,
            cell_id=cell_id,
            log_sequence=i,
            notebook_name=notebook_name,
            log_json=log,
            log_code=log['code'],
            log_path=log['path'],
            log_start=jst2datetime(log['start']),
            log_end=jst2datetime(log['end']),
            log_size=log['size'],
            log_server_signature=log['server_signature'],
            log_uid=log['uid'],
            log_gid=log['gid'],
            log_notebook_path=log['notebook_path'],
            log_lc_notebook_meme=log['lc_notebook_meme'],
            log_execute_reply_status=log['execute_reply_status'],
        ))
    if len(values) == 0:
        return
    engine = create_engine(db_url)
    with Session(engine) as session:
        crud.create_logs(session=session, log_creates=values, skip_exists=True)
        session.commit()


def _load_log_json(log_dir: str, cell_id: str) -> dict:
    """ログ情報を読み取る
    """
    log_json = os.path.join(log_dir, cell_id, cell_id+'.json')
    if not os.path.isfile(log_json):
        return {}

    with open(log_json, 'r', encoding='utf8') as f:
        logs = json.load(f)

    return logs


def log2db(course: str, user_name: str,
           homedir: str = '/jupyter',
           dt_from: datetime = DEFAULT_DT_FROM,
           dt_to: datetime | None = None,
           assignment: str | list = None) -> str:
    """ログファイルを読み取り、DBに登録する

    :param course: コース名
    :type course: string
    :param user_name: 教師ユーザ名
    :type user_name: string
    :param homedir: ホームディレクトリ
    :type homedir: string defaults to '/jupyter'
    :param dt_from: 対象データの始点日時
    :type dt_from: datetime defaults to datetime(1970, 1, 1, timezone.utc)
    :param dt_to: 対象データの終点日時
    :type dt_to: datetime defaults to datetime.now(timezone.utc)
    :param assignment: 課題名 Noneの場合、コース内の全ての課題を対象とする
    :type assignment: string
    :returns: 作成したDBファイルのパス
    :rtype: string
    """

    dt_to = dt_to if dt_to is not None else datetime.now(timezone.utc)
    original_file_dir = 'release'
    teacher_home = os.path.join(homedir, user_name)
    course_path = os.path.join(teacher_home, 'nbgrader', course)

    if not os.path.isdir(course_path):
        raise FileNotFoundError(os.path.join('nbgrader', course))
    log_db_url = os.getenv('LOG_DB_URL', f'sqlite:////{course_path}/exec_history.db')
    init_db(log_db_url)
    nbg_db_path = db_path(user_name, course, homedir)
    students = get_course_students(nbg_db_path, course)
    if assignment is not None:
        # 課題の指定がある場合、「指定されたものかつnbgraderに登録されているもの」が対象
        if isinstance(assignment, str):
            specified_assignment = [assignment]
        elif isinstance(assignment, list):
            specified_assignment = assignment.copy()
        assignments = list(set(specified_assignment) &
                           set(get_course_assignments(user_name, course, homedir)))
    else:
        # 課題の指定が無い場合、nbgraderに登録されているものが全て対象
        assignments = get_course_assignments(user_name, course, homedir)
    update_or_create_log_student(log_db_url, students)

    # cell_idリストの作成
    assign_info = dict()
    for assignment_name in assignments:
        if assignment_name not in assign_info:
            assign_info[assignment_name] = dict(notebooks=list())

        teacher_notebooks = glob.glob(
                                os.path.join(course_path,
                                             original_file_dir,
                                             assignment_name, '*.ipynb'))

        for notebook_path in teacher_notebooks:
            if not os.path.isfile(notebook_path):
                continue
            with open(notebook_path, mode='r', encoding='utf8') as f:
                cell_infos = get_cell_info(json.load(f)['cells'])
            nb_name = os.path.basename(notebook_path)
            update_or_create_cell_id(log_db_url,
                                     nb_name,
                                     assignment_name,
                                     cell_infos)
            assign_info[assignment_name]['notebooks'].append(
                {nb_name: dict(cell_infos=cell_infos)})

    # 学生のログを収集
    for student in students:
        student_local_course_dir = os.path.join(homedir, student,
                                                course)
        if not os.path.isdir(student_local_course_dir):
            continue

        for assign_name, notebooks in assign_info.items():
            student_local_assign_dir = os.path.join(
                student_local_course_dir, assign_name)

            if not os.path.isdir(student_local_assign_dir):
                # 課題未フェッチ
                continue
            student_local_log_dir = os.path.join(
                student_local_assign_dir, '.log')
            if not os.path.isdir(student_local_log_dir):
                # ログ出力無し
                continue
            for notebook in notebooks['notebooks']:
                notebook_name = list(notebook.keys())[0]
                student_local_notebook = os.path.join(
                    student_local_assign_dir,
                    notebook_name)
                if not os.path.isfile(student_local_notebook):
                    # Notebook不存在
                    continue
                for cell_info in notebook[notebook_name]['cell_infos']:
                    # ノートブック上の`lc_cell_meme`に枝番がついていても、
                    # ログ出力先のディレクトリ名には枝番が付かないため、
                    # カットしたuuidで検索する
                    logs = _load_log_json(student_local_log_dir,
                                          remove_uuid_branch(cell_info['cell_id']))

                    if len(logs) > 0:
                        # DBには枝番付きのセルIDを登録する
                        # 教師のノートブック上のセルIDと一致させるため。
                        update_or_create_log(log_db_url, notebook_name,
                                             assign_name,
                                             student, cell_info['cell_id'],
                                             logs,
                                             dt_from, dt_to)

    return log_db_url


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


class TeacherToolsApiHandler(HubAuthenticated, web.RequestHandler):

    _token_authenticated = True

    def initialize(self):
        self.hub_api_url = self.settings["hub_api_url"]
        self.homedir = self.settings["homedir"]

    def check_xsrf_cookie(self):
        return

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

    def json_output(self, status_code=None, reason=None, output={}):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        if status_code:
            self.set_status(status_code, reason)
        if len(output) == 0:
            _output = {}
        else:
            _output = output
        self.write(json.dumps(_output, indent=1, sort_keys=True))

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "application/json")
        if "exc_info" in kwargs:
            exception = kwargs["exc_info"][1]
            if isinstance(exception, web.HTTPError):
                self.log.warning(exception.log_message)
                reason = exception.reason
                if 403 == status_code and not reason:
                    reason = 'Permission denied'
                self.finish({
                    "status": status_code,
                    "reason": reason,
                })
                return
        self.finish({"status": status_code, "reason": "Unknown error"})


class TeacherToolsLogDBHandler(TeacherToolsApiHandler):
    """Update log db"""

    def initialize(self):
        super().initialize()

    @web.authenticated
    async def post(self):
        user = self.get_current_user()
        self.json_data = escape.json_decode(self.request.body)
        try:
            # required params
            # TODO: userのgroupから取る
            course = self.json_data['course']
        except KeyError as e:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Missing required paramater: [{e}]"
            )

        dt_from = self.json_data.get('from')
        dt_to = self.json_data.get('to')
        assignment = self.json_data.get('assignment')
        opt = {}
        if dt_from is not None:
            opt['dt_from'] = datetime.fromisoformat(dt_from)
        if dt_to is not None:
            opt['dt_to'] = datetime.fromisoformat(dt_to)
        if assignment is not None:
            opt['assignment'] = assignment
        try:
            db_path = log2db(course, user["name"], self.homedir, **opt)
        except FileNotFoundError:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Course not found: {course}"
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
        if "teacher" not in user_info['groups']:
            raise web.HTTPError(
                HTTPStatus.FORBIDDEN, "User is not teacher"
            )
        if course_id not in user_info['groups']:
            raise web.HTTPError(
                HTTPStatus.FORBIDDEN, f"User is teacher but not this course: {course_id}"
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

            # 非learner（教師ユーザ）の成績が入っているとMoodle側で400エラーになるため、除く
            if user['name'] == grade['student']:
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

        course_short_name = self.course_shortname(user, self.homedir)
        course_name = self.get_user_info(user)['auth_state'][course_info_key]['title']
        assignments = get_course_assignments(user['name'],
                                             course_short_name,
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
