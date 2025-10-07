FROM quay.io/jupyterhub/jupyterhub:4.1.5

ADD requirements.txt /root
RUN python3 -m pip install --upgrade pip
RUN pip install -r /root/requirements.txt
RUN mkdir -p /opt/jupyterhub
ENV PYTHONPATH "${PYTHONPATH}:/etc/jupyterhub:/opt/jupyterhub"
