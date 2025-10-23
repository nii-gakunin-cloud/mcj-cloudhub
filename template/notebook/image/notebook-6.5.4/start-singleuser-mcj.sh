#!/bin/bash

set -e

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
ln -s /jupytershare/class/$COURSE_SHORTNAME ~/class

# Original in base notebook container image
. /usr/local/bin/start-singleuser.sh $@
