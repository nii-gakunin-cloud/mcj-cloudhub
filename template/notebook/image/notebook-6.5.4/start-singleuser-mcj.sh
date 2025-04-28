#!/bin/bash

set -e

# Custom for mcj
mkdir -p ~/.local/share/jupyter
mkdir -p ~/.jupyter
groupadd -g $STUDENT_GID students && groupadd -g $TEACHER_GID teachers
PYTHON_VERSION=$(python --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
chown $NB_USER:root $CONDA_DIR/lib/python$PYTHON_VERSION/site-packages
chown $NB_USER:root $CONDA_DIR/man/man1/
chown $NB_USER:root $CONDA_DIR/bin/
chown $NB_USER:root ~/.jupyter
chown $NB_USER:root ~/.local
chown $NB_USER:root ~/.local/share/jupyter

jupyter nblineage quick-setup
jupyter nbextension install --py lc_multi_outputs --user
jupyter nbextension enable lc_multi_outputs --user --py

if [ "$COURSEROLE" == "Instructor" ]; then
    jupyter serverextension enable --sys-prefix nbgrader.server_extensions.formgrader
    jupyter nbextension enable --sys-prefix formgrader/main --section=tree
    jupyter nbextension enable --sys-prefix create_assignment/main
    jupyter labextension enable nbgrader:formgrader
    jupyter labextension enable nbgrader:create-assignment
fi

# Original in base notebook container image
. /usr/local/bin/start-singleuser.sh $@