FROM jupyterhub/jupyterhub:4.0.2

ADD requirements.txt /root
RUN python3 -m pip install --upgrade pip && \
    pip install -r /root/requirements.txt
