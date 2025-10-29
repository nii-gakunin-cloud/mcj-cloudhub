from datetime import datetime, timedelta, timezone
import glob
import json
import os
import re

from nbgrader.api import Gradebook, MissingEntry
import sqlite3

JST = timezone(timedelta(hours=+9), 'JST')
LOG_DB_INIT_SQL = os.path.join(
        os.path.dirname(__file__), 'init_log.sql')
DEFAULT_DT_FROM = datetime(1970, 1, 1, tzinfo=timezone.utc)


def jst2datetime(dt: str) -> datetime:
    """JSTのタイムスタンプをdatetime型に変換する

    LC_wrapperに登録されているタイムスタンプ型をタイムゾーン情報を持つdatetime型に変換する。

    :param dt: JSTタイムスタンプ（'%Y-%m-%d %H:%M:%S (JST)'）
    :type dt: string
    :returns: datetime
    :rtype: datetime

    >>> jst2datetime("2024-10-18 19:32:54(JST)")
    datetime.datetime(2024, 10, 18, 19, 32, 54, tzinfo=datetime.timezone(datetime.timedelta(seconds=32400)))
    """
    converted_dt = datetime.strptime(
        dt.replace('(JST)', ' +0900'), '%Y-%m-%d %H:%M:%S %z')
    return converted_dt


def db_path(username: str, coursename: str,
            home_root: str = '/jupyter'):
    p = os.path.join(home_root, username, 'nbgrader',
                     coursename, 'gradebook.db')
    return p


def get_course_students(db_path: str, course_name: str) -> list:
    """コースの学生IDリストを返す

    :param db_path: dbファイルへのパス
    :type db_path: string
    :param course_name: コース名
    :type course_name: string
    :returns: 学生のIDリスト ex. ['student01', 'student02']
    :rtype: list
    """
    if not os.path.isfile(db_path):
        return []
    gb = Gradebook('sqlite:///' + db_path, course_name)
    return [d.id for d in gb.students]


def get_course_assignments(username: str, course_name: str,
                           homedir: str = '/home') -> list:
    """コースの課題リストを返す

    :param username: 教師ユーザ名
    :type username: string
    :param course_name: コース名
    :type course_name: string
    :returns: 課題名リスト ex. ['assignment01', 'assignment02']
    :rtype: list
    """

    gb = Gradebook('sqlite:///' + db_path(username, course_name, homedir),
                   course_name)
    return [d.name for d in gb.assignments]


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


def create_db(db_dir: str, db_name: str = "exec_history.db",
               owner_uid: int = -1, owner_gid: int = -1,
               exist_ok: bool = True) -> str:
    """db(sqlite)を作成する

    :param db_dir: dbファイルを作成するディレクトリ
    :type db_dir: string
    :param db_name: dbファイル名
    :type db_name: string
    :param owner_uid: ファイルのオーナuid -1を指定した場合は変更しない。
    :type owner_uid: int optional defaults to -1
    :param owner_gid: ファイルのオーナgid -1を指定した場合は変更しない。
    :type owner_gid: int optional defaults to -1
    :param exist_ok: Falseの場合、DBが既に存在する場合に例外（FileExistsError）を浮揚する。
                     Trueの場合、何もしない。
    :type exist_ok: bool defaults to True
    :returns: 作成したDBファイルのパス
    :rtype: string
    """

    with open(LOG_DB_INIT_SQL, 'r', encoding='utf8') as f:
        init_sql = f.read()

    db_path = os.path.join(db_dir, db_name)
    if os.path.isfile(db_path):
        if exist_ok:
            return db_path
        else:
            raise FileExistsError(f'DB file Already exists: {db_path}')

    conn = sqlite3.connect(db_path)
    with conn:
        cur = conn.cursor()
        for sql in init_sql.split(";"):
            cur.execute(sql)

    os.chown(db_path, owner_uid, owner_gid)
    os.chmod(db_path, 0o0640)
    return db_path


def insert_db(db_path: str, table: str,
              items: str, values: list) -> None:
    """db(sqlite)にデータを登録する

    :param db_path: dbファイルのパス
    :type db_path: string
    :param table: 挿入先テーブル名
    :type table: string
    :param items: 項目リスト e.g. [id, name]
    :type items: list
    :param values: 登録する値リスト 項目リストと順番が一致していること。
      e.g. [[1, 'student01'], [2, 'student02']]
    :type values: list
    """
    sql = f'insert or ignore into {table} ('
    sql += ','.join(items)
    sql += ') values ('
    sql += ','.join('?' for _ in range(len(items)))
    sql += ')'

    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
    with conn:
        cur = conn.cursor()
        cur = conn.cursor()
        cur.executemany(sql, values)


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
    :type dt_from: datetime defaults to datetime.datetime(1970, 1, 1, timezone.utc)
    :param dt_to: 対象データの終点日時
    :type dt_to: datetime defaults to datetime.now(timezone.utc)
    :param assignment: 課題名 Noneの場合、コース内の全ての課題を対象とする
    :type assignment: string
    :returns: 作成したDBファイルのパス
    :rtype: string
    """

    def _load_log_json(log_dir: str, cell_id: str) -> dict:
        """ログ情報を読み取る
        """
        log_json = os.path.join(log_dir, cell_id, cell_id+'.json')
        if not os.path.isfile(log_json):
            return {}

        with open(log_json, 'r', encoding='utf8') as f:
            logs = json.load(f)

        return logs

    dt_to = dt_to if dt_to is not None else datetime.now(timezone.utc)
    original_file_dir = 'release'
    teacher_home = os.path.join(homedir, user_name)
    course_path = os.path.join(teacher_home, 'nbgrader', course)

    if not os.path.isdir(course_path):
        raise FileNotFoundError(os.path.join('nbgrader', course))

    stat = os.stat(teacher_home)
    log_db_path = create_db(course_path, owner_uid=stat.st_uid)
    nbg_db_path = db_path(user_name, course, homedir)
    students = get_course_students(nbg_db_path, course)
    if assignment is not None:
        # 課題の指定がある場合、「指定されたものかつnbgraderに登録されているもの」が対象
        if isinstance(assignment, str):
            specified_assignment = [assignment]
        elif isinstance(assignment, list):
            specified_assignment = assignment.copy()
        assignments = list(set(specified_assignment) & set(get_course_assignments(user_name, course, homedir)))
    else:
        # 課題の指定が無い場合、nbgraderに登録されているものが全て対象
        assignments = get_course_assignments(user_name, course, homedir)
    update_or_create_log_student(log_db_path, students)

    # cell_idリストの作成
    assign_info = dict()
    for assignment_name in assignments:
        if assignment_name not in assign_info:
            assign_info[assignment_name] = dict(notebooks=list())

        teacher_notebooks = glob.glob(os.path.join(course_path,
                                            original_file_dir,
                                            assignment_name, '*.ipynb'))

        for notebook_path in teacher_notebooks:
            if not os.path.isfile(notebook_path):
                continue
            with open(notebook_path, mode='r', encoding='utf8') as f:
                cell_infos = get_cell_info(json.load(f)['cells'])
            nb_name = os.path.basename(notebook_path)
            update_or_create_cell_id(log_db_path,
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
                    logs = _load_log_json(student_local_log_dir, cell_info['cell_id'])

                    if len(logs) > 0:
                        update_or_create_log(log_db_path, notebook_name, assign_name,
                                            student, cell_info['cell_id'], logs,
                                             dt_from, dt_to)

    return log_db_path


def update_or_create_log_student(db_path: str, students: list):
    """コースの学生一覧をDBに登録する

    :param db_path: DBファイルのパス
    :type db_path: string
    :param students: 学生名リスト e.g. ['student01', 'student02',]
    :type students: list
    """
    if len(students) == 0:
        return
    table = 'student'
    items = ['id',]
    values = [[d] for d in students]
    insert_db(db_path, table, items, values)


def update_or_create_cell_id(db_path: str, notebook_name: str,
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

    table = 'cell'
    items = [
        'id',
        'assignment',
        'section',
        'notebook_name',
        'jupyter_cell_id',
        'nbgrader_cell_id',
    ]
    values = list()
    for cell_info in cell_infos:
        values.append([
            cell_info['cell_id'],
            assignment,
            cell_info['section'],
            notebook_name,
            cell_info['jupyter_cell_id'],
            cell_info['nbgrader_cell_id'],
        ])
    insert_db(db_path, table, items, values)


def update_or_create_log(db_path: str,  notebook_name: str,
                         assignment: str, user_id: str,
                         cell_id: str, logs: list, dt_from: datetime,
                         dt_to: datetime):
    """学生の実行履歴情報をDBに登録する
    ログの実行完了時刻が指定日時内でない場合は登録しない。

    :param db_path: DBファイルのパス
    :type db_path: string
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

    table = 'log'
    items = [
        'assignment',
        'student_id',
        'cell_id',
        'log_sequence',
        'notebook_name',
        'log_json',
        'log_code',
        'log_path',
        'log_start',
        'log_end',
        'log_size',
        'log_server_signature',
        'log_uid',
        'log_gid',
        'log_notebook_path',
        'log_lc_notebook_meme',
        'log_execute_reply_status',
    ]

    values = list()

    for i, log in enumerate(logs):

        if jst2datetime(log['end']) > dt_to or dt_from > jst2datetime(log['end']):
            continue

        values.append([
            assignment,
            user_id,
            cell_id,
            i,
            notebook_name,
            json.dumps(log),
            log['code'],
            log['path'],
            jst2datetime(log['start']),
            jst2datetime(log['end']),
            log['size'],
            log['server_signature'],
            log['uid'],
            log['gid'],
            log['notebook_path'],
            log['lc_notebook_meme'],
            log['execute_reply_status'],
        ])

    if len(values) > 0:
        insert_db(db_path, table, items, values)


def get_grades(course_id, assign, teacher, homedir='/home'):
    """指定されたコース・課題の成績一覧を返す
    [{'max_score': 100.0,
        'student': 'student01',
        'assignment': 'sample01',
        'score': 85.0}]
    """
    gb_dir = db_path(teacher, course_id, homedir)
    # Create the connection to the database
    grades = []
    with Gradebook(f'sqlite:///{gb_dir}') as gb:

        try:
            assignment = gb.find_assignment(assign)
        except MissingEntry:
            return None

        # Loop over each student in the database
        for student in gb.students:

            score = {}
            score['max_score'] = assignment.max_score
            score['student'] = student.id
            score['assignment'] = assignment.name

            try:
                submission = gb.find_submission(assignment.name, student.id)
            except MissingEntry:
                score['score'] = 0.0
            else:
                score['score'] = submission.score

            grades.append(score)
    return grades

