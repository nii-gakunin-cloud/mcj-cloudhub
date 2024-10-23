import argparse
import datetime
import json
import os
import re
import shutil
import time

from nbgrader.api import Gradebook
import sqlite3


def collect_json(home: str = '/home'):
    """
    {
        'teacher01': {
            'home': '/jupyter/teacher01',
            'courses': {
                'course01': {
                    'students': [('mcjt1', 'mcjt', '1', 'mcjt1@example.com', 'mcjt1')]
                }
            }
        }
    }
    """
    teachers = dict()
    for user_home in os.scandir(home):
        if not user_home.is_dir():
            continue

        nbgrader_root = os.path.join(user_home.path, 'nbgrader')

        if not os.path.isdir(nbgrader_root):
            continue

        courses = dict()
        for course in os.scandir(nbgrader_root):
            if not course.is_dir():
                continue

            dbfile = os.path.join(course.path, 'gradebook.db')
            if not os.path.isfile(dbfile):
                continue
            gb = Gradebook('sqlite:///' + dbfile, course.name, )
            students = [d.id for d in gb.students]

            for student in students:
                student_name = student[0]
                student_course_dir = os.path.join(home, student_name, course.name)
                if not os.path.isdir(student_course_dir):
                    continue
                student_assignments = os.scandir(student_course_dir)

                for assignment in student_assignments:
                    if os.path.isdir(os.path.join(assignment, '.log')):
                        _ = shutil.copytree(os.path.join(assignment, '.log'),
                                            os.path.join(nbgrader_root,
                                                         'students_log',
                                                         course.name,
                                                         assignment.name,
                                                         student_name), dirs_exist_ok=True)
        teachers[user_home.name] = dict(home=user_home.path, courses=courses)

def get_meme_ids(cells: list):

    class __NBSection():
        """Markdownの章立てを把握する
        #の数を`level`として、current = [level1, level2, level3, ... , leveln]

        # sec1       [1]

        ## sec1-1    [1, 1]
        ## sec1-2    [1, 2]
        # sec2       [2, 0]
        """
        current = []
        def count_hashes(self, s) -> int:
            match = re.match(r'#+', s)
            return len(match.group(0)) if match else 0

        def increment_section(self, level: int):
            if len(self.current) <= level:
                diff = [0 for i in range(level - len(self.current))]
                self.current.extend(diff)
            self.current[level-1] += 1

        def get_current_section(self):
            return ".".join([str(_) for _ in self.current.copy()])

    meme_ids = list()
    sections = __NBSection()
    for cell in cells:
        if cell['cell_type'] == 'code':
            meme_id = cell['metadata'].get('lc_cell_meme')
            if meme_id is None:
                continue
            meme_ids.append(dict(meme_id=meme_id['current'],
                                 section=sections.get_current_section()))
        elif cell['cell_type'] == 'markdown':
            # 章番号があればインクリメント
            level = sections.count_hashes(cell['source'][0])
            if level > 0:
                sections.increment_section(level)
        else:
            continue
    return meme_ids

def exec_sql(db_path: str, sqls: list, read_only=False):

    if read_only:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(db_path)

    with conn:
        cur = conn.cursor()
        res = list()
        for sql in sqls:
            cur.execute(sql)
            res.append(cur.fetchall())
    return res

def confirm_db(db_dir: str, db_name: str = "exec_history.db",
               owner_uid: int = -1, owner_gid: int = -1):

    init_sql_file = os.path.join(
        os.path.dirname(__file__), 'init_log.sql')

    with open(init_sql_file, 'r', encoding='utf8') as f:
        init_sql = f.read()

    db_path = os.path.join(db_dir, db_name)
    exec_sql(db_path, init_sql.split(";"))
    os.chown(db_path, owner_uid, owner_gid)
    os.chmod(db_path, 0o0640)
    return db_path


def insert_db(db_path: str, sql: str, values: list):
    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
    with conn:
        cur = conn.cursor()
        cur = conn.cursor()
        cur.executemany(sql, values)


def log2db(home: str = '/home'):
    """
    {
        'teacher01': {
            'home': '/jupyter/teacher01',
            'courses': {
                'course01': {
                    'students': [('mcjt1', 'mcjt', '1', 'mcjt1@example.com', 'mcjt1')]
                }
            }
        }
    }
    """
    original_file_dir = 'release'
    
    for user_home in os.scandir(home):
        if not user_home.is_dir():
            continue

        nbgrader_root = os.path.join(user_home.path, 'nbgrader')

        if not os.path.isdir(nbgrader_root):
            continue

        courses = dict()
        for course in os.scandir(nbgrader_root):
            if not course.is_dir():
                continue

            dbfile = os.path.join(course.path, 'gradebook.db')
            if not os.path.isfile(dbfile):
                continue
            stat = os.stat(user_home)
            log_db_pass = confirm_db(course.path, owner_uid=stat.st_uid)

            # コースの課題一覧と受講生一覧を取得
            gb = Gradebook('sqlite:///' + dbfile, course.name)
            students = [d.id for d in gb.students]
            assignments = [d.name for d in gb.assignments]
            courses[course.name] = dict(students=students,
                                        assignments=assignments)
            update_or_create_log_student(log_db_pass, students)

            # meme_idリストの作成
            assign_info = dict() # {assignment_name: [memeids]}
            for assignment_name in assignments:
                if assignment_name not in assign_info:
                    assign_info[assignment_name] = dict(notebooks=list())

                for f in os.scandir(
                    os.path.join(course.path, original_file_dir, assignment_name)):

                    if not f.is_file():
                        continue
                    if os.path.splitext(f)[1] != '.ipynb':
                        continue
                    with open(f, mode='r', encoding='utf8') as notebook:
                        cells = json.load(notebook)['cells']
                    log_ids = get_meme_ids(cells)
                    update_or_create_log_id(log_db_pass,
                                            f.name,
                                            assignment_name,
                                            log_ids)
                    assign_info[assignment_name]['notebooks'].append(
                        {f.name: dict(log_ids=log_ids)})

            for student in students:
                student_name = student
                student_local_course_dir = os.path.join(home, student_name,
                                                        course.name)
                if not os.path.isdir(student_local_course_dir):
                    continue

                for assign_name, notebooks in assign_info.items():
                    student_local_assign_dir = os.path.join(
                        student_local_course_dir, assign_name)
                    if not os.path.isdir(student_local_assign_dir):
                        continue
                    student_local_log_dir = os.path.join(
                        student_local_assign_dir, '.log')
                    if not os.path.isdir(student_local_log_dir):
                        continue
                    for notebook in notebooks['notebooks']:
                        notebook_name = list(notebook.keys())[0]
                        student_local_notebook = os.path.join(
                            student_local_assign_dir,
                            notebook_name)
                        if not os.path.isfile(student_local_notebook):
                            continue

                        for log_id in notebook[notebook_name]['log_ids']:
                            log_json = os.path.join(student_local_log_dir,
                                                    log_id['meme_id'],
                                                    log_id['meme_id']+'.json')
                            logs = load_log_json(log_json, notebook_name,
                                                 log_id['section'])
                            update_or_create_log(log_db_pass, notebook_name, assign_name,
                                                 student_name, log_id['meme_id'], logs)


def update_or_create_log_student(db_pass: str, students: list):

    if len(students) == 0:
        return

    items = [
        'id',
    ]
    values = [[d] for d in students]

    sql = 'insert or ignore into student ('
    sql += ','.join(items)
    sql += ') values ('
    sql += ','.join('?' for _ in range(len(items)))
    sql += ')'
    insert_db(db_pass, sql, values)


def update_or_create_log_id(db_pass: str, notebook_name: str,
                            assignment: str, log_ids: list):

    if len(log_ids) == 0:
        return

    items = [
        'id',
        'assignment',
        'section',
        'notebook_name',
    ]

    values = list()
    for log_id in log_ids:
        values.append([
            log_id['meme_id'],
            assignment,
            log_id['section'],
            notebook_name,
        ])

    sql = 'insert or ignore into log_id ('
    sql += ','.join(items)
    sql += ') values ('
    sql += ','.join('?' for _ in range(len(items)))
    sql += ')'
    insert_db(db_pass, sql, values)


def jst2datetime(dt: str) -> datetime:
    converted_dt = datetime.datetime.strptime(
        dt.replace('(JST)', ' +0900'), '%Y-%m-%d %H:%M:%S %z')
    return converted_dt


def update_or_create_log(db_path: str,  notebook_name: str,
                         assignment: str, user_id: str,
                         log_id: str, logs: list):

    items = [
        'assignment',
        'student_id',
        'log_id',
        'log_sequence',
        'notebook_name',
        'log_whole',
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

        values.append([
            assignment,
            user_id,
            log_id,
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

    sql = 'insert or ignore into log ('
    sql += ','.join(items)
    sql += ') values ('
    sql += ','.join('?' for _ in range(len(items)))
    sql += ')'
    insert_db(db_path, sql, values)


def load_log_json(path: str, nb_name: str,
                  section: str = '') -> dict:

    if not os.path.isfile(path):
        return {}

    with open(path, 'r', encoding='utf8') as f:
        logs = json.load(f)

    for log in logs:
        log['cell_section'] = section
        log['notebook_name'] = nb_name

    return logs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--duration",
        help="Duration(seconds) to collect log. default: 0(Not collect logs)",
        default=60,
        type=int
    )
    parser.add_argument(
        "--home",
        help="Home directory path",
        default="/home",
        type=str
    )
    args = parser.parse_args()

    while True:
        try:
            log2db(args.home)
            time.sleep(args.duration)
        except KeyboardInterrupt:
            print("interrupted")
