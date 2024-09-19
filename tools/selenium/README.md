# Selenium

Seleniumを用いてユーザのログインからsingle-user notebook serverコンテナの起動までを検証するためのツールです。

## 使い方

Jupyterhubの構築などと同様、セットアップ用ノートブック（[812-single-userコンテナ起動確認-selenium](https://github.com/nii-gakunin-cloud/mcj-cloudhub/blob/dev/selenium/notebooks/812-single-user%E3%82%B3%E3%83%B3%E3%83%86%E3%83%8A%E8%B5%B7%E5%8B%95%E7%A2%BA%E8%AA%8D-selenium.ipynb)）を利用して、環境に応じたセットアップを行ってください。

## 構成
```
本ディレクトリ(selenium)
├── docker-compose.yml ... 
├── README.md ... 本ファイル
└── selenium-client/ ... selenium実行用コンテナイメージ資材
    ├── accounts_sample.csv ... テスト用ユーザ定義のサンプル
    ├── Dockerfile ... selenium実行用コンテナイメージ作成用Dockerfile
    ├── main.py ... selenium処理定義
    └── requirements.txt ... 必要なpythonパッケージリスト
```

## Notes  

### 処理詳細

1. `docker compose up`を実行
1. `selenium-executer`コンテナが起動する
1. `selenium-client`コンテナが起動する  
  `docker-compose.yml`の`selenium-client`コンテナ定義の`command`で指定した処理を実行します。  
  実際にseleniumの処理を行う`executer`に`selenium-executer`コンテナを指定しています。
1. `selenium-client/result` 以下に処理結果を記載した`.json`ファイルを出力  

    ```
    {
        "admin": {
            "status": "ok",
            "started": "2024-09-19T07:05:50.484483",
            "detail": [
                {
                    "spawn": "ok"
                },
                {
                    "exec_output": "user test"
                }
            ],
            "finished": "2024-09-19T07:06:11.574919"
        }
    }
    ```
    - `"admin":` ... ユーザ名
    - `"status": "ok"` ... そのユーザの処理が全て正常に終了したことを示す
    - `"started": "2024-09-19T07:05:50.484483"` ... 処理開始日時
    - `"finished": "2024-09-19T07:06:11.574919"` ... 処理終了日時
    - `"spawn": "ok"` ... そのユーザのsingle-user serverの起動に成功したことを示す
    - `"exec_output": "user test"` ... 起動したsingle-user serverで実行したスクリプトの結果を示す（スクリプトを実行するよう設定した場合）

### selenium実行時に指定できる項目

`selenium-client/main.py`を実行する際に指定できるパラメータを記載しています。  
`docker-compose up`で処理を起動する場合、`docker-compose.yml`の`selenium-client`の`command`にパラメータを追加してください。  
seleniumが利用可能な環境であれば、以下のパラメータを指定し、`main.py`単独で実行可能です。

* 必須パラメータ
    * **accounts_file** – テスト対象のユーザ情報一覧。`.csv`, `.yml`, `.yaml`が利用可能。
    * **lms_url** – LMSのログインURL。
    * **selenium_executer** – seleniumのexecuter。実際にseleniumの処理を行う。
* 非必須パラメータ
    * **browser** – テストを行うブラウザ。`selenium_executer`で処理可能なブラウザを指定する。`chrome`, `firefox`等。
    * **headless** – `True`を指定すると、ヘッドレスモードで実行する。指定しない場合、`True`。
    * **tool_id** – LMSにて、JupyterhubにLTI連携でログインするための外部ツールに設定されているツールID。  
        ※ `tool_id`を設定する場合は、`course_name`, `tool_name`の設定は不要。`tool_id`が不明な場合は、`course_name`, `tool_name`を指定することで対象ツールを特定する。
    * **course_name** – LMSにて、JupyterhubにLTI連携でログインするための外部ツールを設定しているコース名。
    * **tool_name** – LMSにて、JupyterhubにLTI連携でログインするための外部ツール名。
    * **src** – ログインしたsingle-user serverで実行する処理を記載したファイルのパス。  
        Notebookを開き、指定されたファイルの内容をそのままセルに記載し、実行する。セルの実行結果として出力された内容が、selenium実行結果ファイル（`selenium-client/result/*`）に出力される。
    * **output_result** – `True`を指定すると、selenium実行結果ファイル（`selenium-client/result/*`）を出力する。指定しない場合、`True`。
