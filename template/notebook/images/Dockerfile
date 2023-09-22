FROM jupyter/scipy-notebook:python-3.8.8

LABEL Description="Jupyter Notebook on Swarm Mode for Yamaguchi University"

USER root

RUN apt-get update && apt-get install -y apt-utils && apt-get clean && rm -rf /var/lib/apt/lists/*

# Shift timezone to Asia/Tokyo.
RUN apt-get update && apt-get install -y tzdata && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV TZ Asia/Tokyo

# Set locale to jp.
RUN apt-get update && apt-get install -y language-pack-ja && update-locale LANG=ja_JP.UTF-8 && rm -rf /var/lib/apt/lists/*
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

RUN apt-get update && apt-get install -y build-essential && apt-get clean

RUN groupadd -g 11000 students && groupadd -g 22000 teachers
RUN rm -fr /usr/local/bin/start.sh && rm -fr /usr/local/bin/start-singleuser.sh
ADD start.sh /usr/local/bin/start.sh
ADD start-singleuser.sh /usr/local/bin/start-singleuser.sh
RUN chmod 4755 /usr/local/bin/start.sh && chmod 4755 /usr/local/bin/start-singleuser.sh
ENV LDAP_SEREVER "{{ldap_server}}"
ENV LDAP_BASE_DN "{{ldap_base}}"
RUN DEBIAN_FRONTEND=noninteractive apt-get install -qq libnss-ldap libpam-ldap ldap-utils
ADD ldap-auth-config /etc/auth-client-config/profile.d/ldap-auth-config
RUN echo "SASL_NOCANON    off"                  > /etc/ldap.conf ;\
    echo "BASE $LDAP_BASE_DN"                  >> /etc/ldap.conf ;\
    echo "URI ldap://$LDAP_SEREVER/"           >> /etc/ldap.conf ;\
    echo "ldap_version 3"                      >> /etc/ldap.conf ;\
    echo "rootbinddn cn=Manager,$LDAP_BASE_DN" >> /etc/ldap.conf ;\
    echo "pam_password md5"                    >> /etc/ldap.conf ;\
    echo "nss_initgroups_ignoreusers backup,bin,daemon,games,gnats,irc,libuuid,list,lp,mail,man,news,proxy,root,sshd,sync,sys,syslog,uucp,www-data" >> /etc/ldap.conf
RUN cp /etc/nsswitch.conf /etc/nsswitch.conf.org
RUN sed -e "s/^passwd:.*$/passwd:         files systemd ldap/g" /etc/nsswitch.conf.org | sed -e "s/^group:.*$/group:          files systemd ldap/g" - | sed -e "s/^shadow:.*$/shadow:         files ldap/g" - > /etc/nsswitch.conf
RUN rm -fr /etc/nsswitch.conf.org
RUN mkdir /jupytershare
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/bin/:/usr/sbin:/bin:/sbin:${PATH}
ADD nbgrader_config.py /etc/jupyter/nbgrader_config.py
RUN chmod 644 /etc/jupyter/nbgrader_config.py && chown root.users /etc/jupyter/nbgrader_config.py

USER jovyan
ADD .gitconfig /home/jovyan/.gitconfig
RUN conda install -y conda-build

RUN pip3 install jupyter_contrib_nbextensions
RUN pip3 install jupyter_nbextensions_configurator
RUN pip3 install autopep8

RUN pip3 install nbgrader==0.6.1 nbconvert[webpdf] sqlalchemy==1.3.23 jinja2==3.0.3
RUN jupyter nbextension enable --sys-prefix codefolding/main
RUN jupyter nbextension enable --section edit codefolding/edit
RUN jupyter nbextension enable --sys-prefix toc2/main
RUN jupyter nbextension enable --sys-prefix code_prettify/autopep8
RUN jupyter nbextension enable --sys-prefix limit_output/main
RUN jupyter nbextension install --sys-prefix --py nbgrader --overwrite
RUN jupyter nbextension enable --sys-prefix --py nbgrader
RUN jupyter serverextension enable --sys-prefix --py nbgrader
RUN jupyter nbextension disable --sys-prefix create_assignment/main
RUN jupyter nbextension disable --sys-prefix formgrader/main --section=tree
RUN jupyter serverextension disable --sys-prefix nbgrader.server_extensions.formgrader
ADD convert.sh /home/jovyan/convert.sh
RUN /home/jovyan/convert.sh && rm -fr /home/jovyan/convert.sh
RUN conda clean --all
RUN sed -i -e 's/check_directory(self\.root, write=True, execute=True)/check_directory(self\.root, write=False, execute=True)/' /opt/conda/lib/python3.8/site-packages/nbgrader/exchange/exchange.py
RUN sed -i -e 's/\[ST_MODE\] \& 0o777/\[ST_MODE\] \& 0o755/' /opt/conda/lib/python3.8/site-packages/nbgrader/exchange/release_assignment.py
RUN sed -i -e 's/perms \& 0o777/perms \& 0o755/' /opt/conda/lib/python3.8/site-packages/nbgrader/exchange/release_assignment.py
RUN cat /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py | sed -n -e '/\#!/,/class NbGraderApp(NbGrader):/p' | sed "/class NbGraderApp(NbGrader):/d" > /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp
RUN echo "if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):" >> /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp
RUN echo "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())" >> /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp
RUN echo "" >> /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp
RUN cat /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py | sed -n '/class NbGraderApp(NbGrader):/,$p' >> /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp
RUN rm /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py
RUN mv /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py.tmp /opt/conda/lib/python3.8/site-packages/nbgrader/apps/nbgraderapp.py
RUN rm /opt/conda/lib/python3.8/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_submissions.js
ADD manage_submissions.js /opt/conda/lib/python3.8/site-packages/nbgrader/server_extensions/formgrader/static/js/manage_submissions.js
RUN sed -i -e 's/return 660 if self\.coursedir\.groupshared else 640/return 664 if self\.coursedir\.groupshared else 644/g' /opt/conda/lib/python3.8/site-packages/nbgrader/converters/generate_feedback.py
RUN pip3 install traitlets==5.9.0