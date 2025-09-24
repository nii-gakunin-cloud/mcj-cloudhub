FROM docker.io/bitnami/moodle:4.5

RUN apt-get update \
  && apt-get install -y curl unzip \
  && rm -rf /var/lib/apt/lists/*

# Language settings(ja)
RUN echo "ja_JP.UTF-8 UTF-8" >> /etc/locale.gen && locale-gen
RUN curl -sSOL https://download.moodle.org/download.php/direct/langpack/4.5/ja.zip \
  && unzip ja.zip -d /bitnami/moodledata/lang/ \
  && rm ja.zip