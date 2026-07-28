FROM jupyterhub/jupyterhub:5.4.2

ENV PYTHONPATH="${PYTHONPATH}:/etc/jupyterhub:/opt/jupyterhub"
ADD requirements.txt /root
RUN python3 -m pip install --upgrade pip && \
    pip install -r /root/requirements.txt

COPY . /etc/jupyterhub
WORKDIR /etc/jupyterhub
