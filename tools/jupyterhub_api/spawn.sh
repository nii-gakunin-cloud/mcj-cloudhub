#!/bin/bash

data='{
  "courserole":"Learner",
  "course":"'$5'",
  "uid_number":"'$2'",
  "gid_number":"'$3'",
  "student_gid":"601",
  "teacher_gid":"600"
}'
curl -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: token $4" \
    -d "$data" http://localhost:8000/hub/api/users/$1/server