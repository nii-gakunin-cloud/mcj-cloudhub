import requests
import urllib


def get_course_students_by_lms_api(token, courseid, iss):

    url = f'{iss}/webservice/rest/server.php'
    params = {
        'wstoken': token,
        'wsfunction': 'core_enrol_get_enrolled_users',
        'courseid': courseid,
        'moodlewsrestformat': 'json',
    }
    headers = {
        "content-type": "application/json"
    }
    params = urllib.parse.urlencode(params)
    response = requests.get(
        url,
        headers=headers,
        params=params,
    )

    students = list()
    for member in response.json():

        if not any(role['shortname'] == 'student' for role in member['roles']):
            continue

        students.append(
            dict(
                id=member['username'],
                first_name=member['firstname'],
                last_name=member['lastname'],
                email=member['email'],
                lms_user_id=member['id']))

    return students
