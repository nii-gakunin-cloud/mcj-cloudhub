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

export JUPYTER_CONFIG_PATH=/jupyter/$NB_USER/nbgrader/$MOODLECOURSE:$JUPYTER_CONFIG_PATH
export PATH=/opt/local/bin:$NB_USER/.local/bin:$NB_USER/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/conda/bin:/home/$NB_USER/tools:$PATH

exec_sh () {
    for script in $1; do
        if [ -f "$script" ]; then
            source "$script" >> ~/custom_installer.log 2>&1 || true
        fi
    done
}

if [ "$COURSEROLE" == "Instructor" ]; then
    jupyter serverextension enable --sys-prefix nbgrader.server_extensions.formgrader
    jupyter nbextension enable --sys-prefix formgrader/main --section=tree
    jupyter nbextension enable --sys-prefix create_assignment/main
    jupyter labextension enable nbgrader:formgrader
    jupyter labextension enable nbgrader:create-assignment
fi
if [ ! -z "$ENABLE_CUSTOM_SETUP" ]; then
    if [ "$COURSEROLE" == "Instructor" ]; then
        exec_sh "/opt/local/sbin/*.sh" "custom_installer.log"
        option_dir=/home/$NB_USER/local
        if [ ! -L $option_dir ]; then
          ln -s /opt/local $option_dir
        fi
    else
        exec_sh "/opt/local/sbin/*.sh"
    fi
fi

class_dir=/home/$NB_USER/class
if [ -L $class_dir ]; then
    unlink $class_dir
fi
ln -s /jupytershare/class/$MOODLECOURSE ~/class

# Original in base notebook container image
. /usr/local/bin/start-singleuser.sh $@
