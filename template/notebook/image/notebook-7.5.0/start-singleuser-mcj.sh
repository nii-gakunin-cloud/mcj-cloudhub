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
    jupyter server extension enable --sys-prefix nbgrader.server_extensions.formgrader
    jupyter labextension enable @jupyter/nbgrader:formgrader
    jupyter labextension enable @jupyter/nbgrader:create-assignment
fi

custom_setup_value_lower=$(echo "$ENABLE_CUSTOM_SETUP" | tr '[:upper:]' '[:lower:]')
if [ ! -z "$custom_setup_value_lower" ] && [ "$custom_setup_value_lower" != "false" ] && [ "$custom_setup_value_lower" != "no" ]; then
    shared_bin='/opt/local/bin'
    shared_sbin='/opt/local/sbin'
    custom_setup_log="custom_installer.log"
    if [ "$COURSEROLE" == "Instructor" ]; then
        exec_sh "$shared_sbin/*.sh" $custom_setup_log
        option_dir=/home/$NB_USER/local
        if [ ! -L $option_dir ]; then
          ln -s /opt/local $option_dir
        fi
        if [ -d "$shared_bin" ]; then
          export PATH="$PATH:$shared_bin"
        fi
    else
        exec_sh "$shared_sbin/*.sh"
        if [ -d "$shared_bin" ]; then
          export PATH="$PATH:$shared_bin"
        fi
    fi
fi

class_dir=/home/$NB_USER/class
if [ -L $class_dir ]; then
    unlink $class_dir
fi
ln -s /jupytershare/class/$COURSE_SHORTNAME ~/class
