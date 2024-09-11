# username, uidnum, gidnum, jupyterhub token
curl -X POST http://localhost:8000/hub/api/users/$1/server \
        -H "Content-Type: application/json" \
        -H "Authorization: token $4" \
        -d '{"COURSEROLE": "Learner", "MOODLECOURSE": "$3", "NB_UID": "$2", "uid_number": "$2", "gid_number": "$3", "STUDENT_GID": 601, "TEACHER_GID": 600}'