FROM jupyter/scipy-notebook:notebook-6.5.4

LABEL Description="Single-user notebook server container image for MCJ-CloudHub"

USER root

RUN apt-get update && \
    apt-get install -y apt-utils vim tzdata language-pack-ja build-essential && \
    apt-get clean

# Shift timezone to Asia/Tokyo.
ENV TZ Asia/Tokyo

# Set locale to jp.
RUN update-locale LANG=ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

# setup for jupyter
RUN rm -fr /usr/local/bin/start.sh && rm -fr /usr/local/bin/start-singleuser.sh
ADD start.sh /usr/local/bin/start.sh
ADD start-singleuser.sh /usr/local/bin/start-singleuser.sh
RUN chmod 4755 /usr/local/bin/start.sh && chmod 4755 /usr/local/bin/start-singleuser.sh
RUN DEBIAN_FRONTEND=noninteractive apt-get install -qq libnss-ldap libpam-ldap ldap-utils
ADD ldap-auth-config /etc/auth-client-config/profile.d/ldap-auth-config
RUN cp /etc/nsswitch.conf /etc/nsswitch.conf.org
RUN sed -e "s/^passwd:.*$/passwd:         files systemd ldap/g" /etc/nsswitch.conf.org | sed -e "s/^group:.*$/group:files systemd ldap/g" - | sed -e "s/^shadow:.*$/shadow:         files ldap/g" - > /etc/nsswitch.conf
RUN rm -fr /etc/nsswitch.conf.org
RUN mkdir /jupytershare
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/bin/:/usr/sbin:/bin:/sbin:${PATH}
ADD nbgrader_config.py /etc/jupyter/nbgrader_config.py
RUN chmod 644 /etc/jupyter/nbgrader_config.py && chown root.users /etc/jupyter/nbgrader_config.py
ADD ldap.conf /etc/ldap.conf

RUN pip install jupyter_contrib_nbextensions
RUN jupyter contrib nbextension install --sys-prefix
RUN jupyter nbextensions_configurator enable --user
RUN jupyter serverextension enable --sys-prefix --py jupyter_nbextensions_configurator

RUN pip3 install jupyterlab-language-pack-ja-JP
RUN pip3 install nbgrader==0.8.5 sqlalchemy==1.4.49 jinja2==3.0.3

RUN jupyter nbextension install --sys-prefix --py nbgrader --overwrite
RUN jupyter nbextension enable --sys-prefix --py nbgrader

RUN pip install git+https://github.com/NII-cloud-operation/Jupyter-LC_wrapper
RUN python -m lc_wrapper.ipython.install
RUN jupyter nbextension install --py lc_wrapper --sys-prefix
RUN jupyter nbextension enable --py lc_wrapper --sys-prefix
RUN jupyter nbextension disable --sys-prefix formgrader/main --section=tree
RUN jupyter serverextension disable --sys-prefix nbgrader.server_extensions.formgrader
RUN jupyter nbextension disable --sys-prefix course_list/main --section=tree
RUN jupyter serverextension disable --sys-prefix nbgrader.server_extensions.course_list
RUN jupyter serverextension disable --sys-prefix nbgrader.server_extensions.create_assignment
RUN jupyter nbextension disable --sys-prefix create_assignment/main

RUN rm -rf /var/lib/apt/lists/*

# setup files for Nbgrader
RUN sed -i 's/664/660/g' /opt/conda/lib/python3.11/site-packages/nbgrader/converters/generate_feedback.py
RUN sed -i 's/644/640/g' /opt/conda/lib/python3.11/site-packages/nbgrader/converters/generate_feedback.py
RUN sed -i -e 's/check_directory(self\.root, write=True, execute=True)/check_directory(self\.root, write=False, execute=True)/' /opt/conda/lib/python3.11/site-packages/nbgrader/exchange/default/exchange.py
RUN sed -i -e 's/\[ST_MODE\] \& 0o777/\[ST_MODE\] \& 0o755/' /opt/conda/lib/python3.11/site-packages/nbgrader/exchange/default/release_assignment.py
RUN sed -i -e 's/perms \& 0o777/perms \& 0o755/' /opt/conda/lib/python3.11/site-packages/nbgrader/exchange/default/release_assignment.py
RUN sed -i -e 's/return 660 if self\.coursedir\.groupshared else 640/return 664 if self\.coursedir\.groupshared else 644/g' /opt/conda/lib/python3.11/site-packages/nbgrader/converters/generate_feedback.py
HEALTHCHECK  --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -O- --no-verbose --tries=1 http://localhost:8888${JUPYTERHUB_SERVICE_PREFIX:-/}api || exit 1
RUN rm /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_assignments.js
ADD manage_assignments.js /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_assignments.js
ADD gradebook_assignments.js /opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/static/js/gradebook_assignments.js

