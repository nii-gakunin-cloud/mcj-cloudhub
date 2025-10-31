#!/bin/bash

groupadd -g $STUDENT_GID students && groupadd -g $TEACHER_GID teachers
runtime_dir=$HOME/.local/share/jupyter/runtime/
mkdir -p $runtime_dir
chown $NB_USER:root $runtime_dir