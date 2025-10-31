from datetime import timedelta, timezone
import os

from nbgrader.api import Gradebook, MissingEntry


JST = timezone(timedelta(hours=+9), 'JST')
LOG_DB_INIT_SQL = os.path.join(
        os.path.dirname(__file__), 'init_log.sql')


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
