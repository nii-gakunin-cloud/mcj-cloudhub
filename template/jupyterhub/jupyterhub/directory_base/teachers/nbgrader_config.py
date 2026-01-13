import getpass
import os

from nbgrader.api import Gradebook


# Configuration file for nbgrader-generate-config.

c = get_config()  # noqa

NBG_STUDENTS = []
COURSE_NAME_SHORT = os.environ['MOODLECOURSE']
NBG_USER_DIR = f'/home/{getpass.getuser()}/nbgrader'
GRADEBOOK_DB = f'sqlite:///{NBG_USER_DIR}/{COURSE_NAME_SHORT}/gradebook.db'

gb = Gradebook(GRADEBOOK_DB, COURSE_NAME_SHORT, None)

for student in NBG_STUDENTS:
    record = {"first_name": student['first_name'],
              "last_name": student['last_name'],
              "email": student['email'],
              "lms_user_id": student['id']}
    gb.update_or_create_student(student['id'], **record)

c.CourseDirectory.root = f'{NBG_USER_DIR}/{COURSE_NAME_SHORT}'
c.NbGrader.logfile = f'{NBG_USER_DIR}/nbgrader.log'
c.CourseDirectory.course_id = COURSE_NAME_SHORT
c.CourseDirectory.db_url = GRADEBOOK_DB
c.IncludeHeaderFooter.header = ''
c.ExecutePreprocessor.timeout = 300
c.NotebookClient.startup_timeout = 120
c.CourseDirectory.ignore.extend(['.log', ])

c.Exchange.path_includes_course = True
c.Exchange.root = '/jupytershare/nbgrader/exchange'
