FROM quay.io/jupyter/scipy-notebook:notebook-7.5.0

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

# setup for jupyter
COPY ldap-auth-config /etc/auth-client-config/profile.d/ldap-auth-config
COPY ldap.conf /etc/ldap.conf
RUN cp /etc/nsswitch.conf /etc/nsswitch.conf.org
RUN sed -e "s/^passwd:.*$/passwd:         files systemd ldap/g" /etc/nsswitch.conf.org | sed -e "s/^group:.*$/group:files systemd ldap/g" - | sed -e "s/^shadow:.*$/shadow:         files ldap/g" - > /etc/nsswitch.conf
RUN rm -fr /etc/nsswitch.conf.org
RUN mkdir -p /jupytershare /opt/local/bin
ENV PATH=/opt/local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin/:/usr/sbin:/bin:/sbin:${PATH}

ENV lc_wrapper_release_tag=1.3.2.rc0 \
    lc_wrapper_release_url=https://github.com/NII-cloud-operation/Jupyter-LC_wrapper/releases/download/ \
    nblineage_release_tag=0.2.0.rc3 \
    nblineage_release_url=https://github.com/NII-cloud-operation/Jupyter-LC_nblineage/releases/download/ \
    lc_index_release_tag=0.2.0.rc6 \
    lc_index_release_url=https://github.com/NII-cloud-operation/Jupyter-LC_index/releases/download/

RUN pip3 --no-cache-dir install jupyter_nbextensions_configurator && \
    pip3 install jupyterlab-language-pack-ja-JP \
                 nbgrader==0.9.5 jupyterhub==5.4.2 \
                 ${nblineage_release_url}${nblineage_release_tag}/nblineage-${nblineage_release_tag}.tar.gz \
                 ${lc_wrapper_release_url}${lc_wrapper_release_tag}/lc_wrapper-${lc_wrapper_release_tag}.tar.gz \
                 ${lc_index_release_url}${lc_index_release_tag}/lc_index-${lc_index_release_tag}.tar.gz \
                 bash_kernel \
                 elasticsearch

RUN pip --no-cache-dir install six bash_kernel && \
    jupyter nblineage quick-setup --sys-prefix && \
    jupyter nbclassic-extension install --py lc_index --sys-prefix && \
    jupyter nbclassic-extension enable --py lc_index --sys-prefix && \
    jupyter nbclassic-extension install --py lc_wrapper --sys-prefix && \
    jupyter nbclassic-extension enable --py lc_wrapper --sys-prefix && \
    jupyter server extension disable --sys-prefix nbgrader.server_extensions.formgrader && \
    jupyter server extension disable --sys-prefix nbgrader.server_extensions.course_list && \
    jupyter labextension disable @jupyter/nbgrader:formgrader && \
    jupyter labextension disable @jupyter/nbgrader:course-list && \
    jupyter labextension disable @jupyter/nbgrader:create-assignment && \
    rm -rf /var/lib/apt/lists/*

ARG PATCH_DIR=/tmp/patches
COPY patches $PATCH_DIR

# setup files for Nbgrader
COPY nbgrader/nbgrader_config.py /etc/jupyter/nbgrader_config.py
RUN chmod 644 /etc/jupyter/nbgrader_config.py && chown root.users /etc/jupyter/nbgrader_config.py
RUN patch /opt/conda/lib/python3.13/site-packages/nbgrader/exchange/default/exchange.py $PATCH_DIR/exchange.py.patch && \
    patch /opt/conda/lib/python3.13/site-packages/nbgrader/exchange/default/release_assignment.py $PATCH_DIR/release_assignment.py.patch

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

# Setup kernels
# Swap default ipython kernel to lc_wrapper kernel.
RUN echo "c.MultiKernelManager.kernel_manager_class = 'lc_wrapper.LCWrapperKernelManager'" > $CONDA_DIR/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.KernelManager.shutdown_wait_time = 10.0" >> $CONDA_DIR/etc/jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.kernel_spec_manager_class = 'lc_wrapper.LCWrapperKernelSpecManager'" >> $CONDA_DIR/etc/jupyter/jupyter_notebook_config.py

RUN <<EOF
mkdir -p /tmp/kernels/python3-wrapper /tmp/wrapper-kernels/python3 && \
cat << EOT > /tmp/kernels/python3-wrapper/kernel.json
{
    "argv": [
        "/opt/conda/bin/python",
        "-m",
        "lc_wrapper.ipython",
        "-f",
        "{connection_file}"
    ],
    "display_name": "Python 3 (LC_wrapper)",
    "language": "python",
    "env": {"PYTHONUSERBASE": "/tmp/pip"}
}
EOT
cat << EOT > /tmp/wrapper-kernels/python3/kernel.json
{
    "argv": [
        "/opt/conda/bin/python",
        "-m",
        "lc_wrapper.ipython",
        "-f",
        "{connection_file}"
    ],
    "display_name": "Python 3",
    "language": "python",
    "env": {"PYTHONUSERBASE": "/tmp/pip"}
}
EOT
EOF

RUN jupyter labextension enable lc_wrapper && \
    jupyter kernelspec install /tmp/kernels/python3-wrapper --sys-prefix && \
    jupyter wrapper-kernelspec install /tmp/wrapper-kernels/python3 --sys-prefix

HEALTHCHECK NONE

# ref: https://jupyter-docker-stacks.readthedocs.io/en/latest/using/common.html#startup-hooks
# Executed before standard setup
COPY start-notebook-hook-mcj.sh /usr/local/bin/start-notebook.d/start-notebook-hook-mcj.sh

# Executed after standard setup, before right before the Server launches
COPY start-singleuser-mcj.sh /usr/local/bin/before-notebook.d/start-singleuser-mcj.sh
