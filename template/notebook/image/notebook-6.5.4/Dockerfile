FROM jupyter/scipy-notebook:notebook-6.5.4

LABEL Description="Single-user notebook server container image for MCJ-CloudHub"

USER root

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -qq apt-utils \
                        vim tzdata \
                        language-pack-ja \
                        build-essential \
                        libnss-ldap \
                        libpam-ldap \
                        ldap-utils && \
    apt-get clean

# Shift timezone to Asia/Tokyo.
ENV TZ=Asia/Tokyo

# Set locale to jp.
RUN update-locale LANG=ja_JP.UTF-8
ENV LANG=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8

# Init settings
COPY start-notebook-mcj.sh /usr/local/bin/start-notebook-mcj.sh
COPY start-singleuser-mcj.sh /usr/local/bin/start-singleuser-mcj.sh
RUN chmod 4755 /usr/local/bin/start-notebook-mcj.sh /usr/local/bin/start-singleuser-mcj.sh
CMD ["start-notebook-mcj.sh"]
HEALTHCHECK NONE

# setup for jupyter
COPY ldap-auth-config /etc/auth-client-config/profile.d/ldap-auth-config
COPY ldap.conf /etc/ldap.conf
RUN cp /etc/nsswitch.conf /etc/nsswitch.conf.org
RUN sed -e "s/^passwd:.*$/passwd:         files systemd ldap/g" /etc/nsswitch.conf.org | sed -e "s/^group:.*$/group:files systemd ldap/g" - | sed -e "s/^shadow:.*$/shadow:         files ldap/g" - > /etc/nsswitch.conf
RUN rm -fr /etc/nsswitch.conf.org
RUN mkdir -p /jupytershare /opt/local/bin
ENV PATH=/opt/local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin/:/usr/sbin:/bin:/sbin:${PATH}

RUN pip3 install jupyter-server>2 \
                 jupyter_contrib_nbextensions \
                 jupyter_nbextensions_configurator \
                 jupyterlab-language-pack-ja-JP \
                 nbgrader==0.8.5 jupyterhub==4.0.2 \
                 git+https://github.com/NII-cloud-operation/Jupyter-multi_outputs \
                 git+https://github.com/NII-cloud-operation/Jupyter-LC_nblineage \
                 git+https://github.com/NII-cloud-operation/Jupyter-LC_index \
                 git+https://github.com/NII-cloud-operation/Jupyter-LC_wrapper

RUN pip3 install --upgrade jupyter-server==2.12.5

RUN python -m lc_wrapper.ipython.install && \
    jupyter nbextension install --sys-prefix --py notebook_index && \
    jupyter nbextension enable --sys-prefix --py notebook_index && \
    jupyter nbextension install --sys-prefix --py nbgrader --overwrite && \
    jupyter nbextension enable --sys-prefix --py nbgrader && \
    jupyter nbextension install --py lc_wrapper --sys-prefix && \
    jupyter nbextension enable --py lc_wrapper --sys-prefix && \
    jupyter nbextension disable --sys-prefix formgrader/main --section=tree && \
    jupyter serverextension disable --sys-prefix nbgrader.server_extensions.formgrader && \
    jupyter nbextension disable --sys-prefix course_list/main --section=tree && \
    jupyter serverextension disable --sys-prefix nbgrader.server_extensions.course_list && \
    jupyter nbextension disable --sys-prefix create_assignment/main && \
    jupyter labextension disable nbgrader:formgrader && \
    jupyter labextension disable nbgrader:course-list && \
    jupyter labextension disable nbgrader:create-assignment && \
    rm -rf /var/lib/apt/lists/*

# For iframe
RUN <<EOF
mkdir -p /usr/local/etc/jupyter
cat << EOT > /usr/local/etc/jupyter/jupyter_server_config.py
c = get_config()  # noqa: F821
c.ServerApp.tornado_settings = {
    'headers': {
        'Content-Security-Policy': "frame-ancestors 'self'"
    }
}
EOT
EOF

ARG PATCH_DIR=/tmp/patches
COPY patches $PATCH_DIR

# setup files for Nbgrader
COPY nbgrader/nbgrader_config.py /etc/jupyter/nbgrader_config.py
RUN chmod 644 /etc/jupyter/nbgrader_config.py && chown root.users /etc/jupyter/nbgrader_config.py
RUN patch /opt/conda/lib/python3.11/site-packages/nbgrader/exchange/default/exchange.py $PATCH_DIR/exchange.py.patch && \
    patch /opt/conda/lib/python3.11/site-packages/nbgrader/exchange/default/release_assignment.py $PATCH_DIR/release_assignment.py.patch && \
    patch /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_assignments.js $PATCH_DIR/manage_assignments.js.patch && \
    patch /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_submissions.js $PATCH_DIR/manage_submissions.js.patch && \
    patch /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/gradebook_assignments.js $PATCH_DIR/gradebook_assignments.js.patch
