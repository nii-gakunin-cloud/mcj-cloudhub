FROM jupyterhub/jupyterhub:4.0.2

ADD requirements.txt /root
RUN python3 -m pip install --upgrade pip
RUN pip install -r /root/requirements.txt
RUN mkdir -p /opt/jupyterhub
ENV PYTHONPATH "${PYTHONPATH}:/etc/jupyterhub:/opt/jupyterhub"
