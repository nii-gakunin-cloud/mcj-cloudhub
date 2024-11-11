FROM python:3.10-slim

# 必要なパッケージをインストール
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# スクリプトをコンテナにコピー
COPY main.py /app/main.py
