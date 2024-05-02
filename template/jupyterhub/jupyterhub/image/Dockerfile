FROM jupyterhub/jupyterhub:4.0.2

RUN python3 -m pip install --upgrade pip
ADD requirements.txt /root
RUN pip install -r /root/requirements.txt
RUN groupadd teachers -g 22000 && groupadd students -g 11000
RUN mkdir /opt/jupyterhub
ENV PYTHONPATH "${PYTHONPATH}:/etc/jupyterhub:/opt/jupyterhub"
ADD mcj_spawner.py /opt/jupyterhub
