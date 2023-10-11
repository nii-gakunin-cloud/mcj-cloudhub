FROM jupyterhub/jupyterhub:4.0.2

RUN python3 -m pip install --upgrade pip
RUN pip install dockerspawner==12.1.0 jupyterhub-ltiauthenticator==1.6.1 \
    jupyter_client==8.1.0 ldap3 pymysql==1.0.2 mysql-connector-python==8.0.23
RUN groupadd teachers -g 22000 && groupadd students -g 11000