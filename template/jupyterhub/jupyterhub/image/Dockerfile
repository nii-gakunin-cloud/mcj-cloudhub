FROM jupyterhub/jupyterhub:4.0.2

ARG gid_teacher
ARG gid_student

RUN python3 -m pip install --upgrade pip
ADD requirements.txt /root
RUN pip install -r /root/requirements.txt
RUN groupadd teachers -g $gid_teacher && groupadd students -g $gid_student
RUN mkdir /opt/jupyterhub
ENV PYTHONPATH "${PYTHONPATH}:/etc/jupyterhub:/opt/jupyterhub"
ADD mcj_spawner.py /opt/jupyterhub
