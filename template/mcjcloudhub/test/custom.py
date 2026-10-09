

def get_course_students(auth_state: dict, course_name: str) -> list:
    """コースの学生を取得するカスタム関数。
    NRPSやMoodle APIでの取得が難しい場合に、独自の実装をおこなう。

    Args:
        auth_state (dict): 認証状態を表す辞書。LTI 1.3のペイロードが含まれる。
    Returns:
        list: List of students in the course, each student is represented as a dict with keys
        eg.)
        [{'id': 'student', 'first_name': 'one', 'last_name': 'gakusei', 'email': 'gakuseione@example.com', 'lms_user_id': '3'},
        {'id': 'teacher', 'first_name': '1', 'last_name': 'sensei', 'email': 'sensei1@example.com', 'lms_user_id': '4'}]
    """
    return [{'id': 'student', 'first_name': 'edited-1', 'last_name': 'gakusei', 'email': 'gakuseione@example.com', 'lms_user_id': '3'},
            {'id': 'teacher', 'first_name': '1', 'last_name': 'sensei', 'email': 'sensei1@example.com', 'lms_user_id': '4'}]