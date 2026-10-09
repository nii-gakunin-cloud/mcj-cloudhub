# 動作確認ツール

Seleniumを用いてユーザのログインからsingle-user notebook serverコンテナの起動までを検証するためのツールです。

## 使い方

Jupyterhubの構築などと同様、セットアップ用ノートブック（[812-single-userコンテナ起動確認-selenium](https://github.com/nii-gakunin-cloud/mcj-cloudhub/blob/dev/selenium/notebooks/812-single-user%E3%82%B3%E3%83%B3%E3%83%86%E3%83%8A%E8%B5%B7%E5%8B%95%E7%A2%BA%E8%AA%8D-selenium.ipynb)）を利用して、環境に応じたセットアップを行ってください。

## 構成

```
本ディレクトリ(selenium)
├── README.md               ... 本ファイル
├── docker-compose.yml
└── selenium-client/        ... selenium実行用コンテナイメージ資材
    ├── accounts_sample.csv ... テスト用ユーザ定義のサンプル
    ├── Dockerfile          ... selenium実行用コンテナイメージ作成用Dockerfile
    ├── main.py             ... selenium処理定義
    └── requirements.txt    ... 必要なpythonパッケージリスト
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

    |項目|意味|
    |-|-|
    |`admin`|ユーザ名|
    |`"status": "ok"`|そのユーザの処理が全て正常に終了したことを示す|
    |`"started": "2024-09-19T07:05:50.484483"`|処理開始日時|
    |`"finished": "2024-09-19T07:06:11.574919"`|処理終了日時|
    |`"spawn": "ok"`|そのユーザのsingle-user serverの起動に成功したことを示す|
    |`"exec_output": "user test"`|起動したsingle-user serverで実行したスクリプトの結果を示す（スクリプトを実行するよう設定した場合）|

### selenium実行時に指定できる項目

`selenium-client/main.py`を実行する際に指定できるパラメータを記載しています。  
`docker-compose up`で処理を起動する場合、`docker-compose.yml`の`selenium-client`の`command`にパラメータを追加してください。  
seleniumが利用可能な環境であれば、以下のパラメータを指定し、`main.py`単独で実行可能です。

* 必須パラメータ  

    |項目名|指定方法|概要|説明|
    |-|-|-|-|
    |accounts_file|`<accounts_file>`|テスト対象のユーザ情報を記載したファイル|`.csv`, `.yml`, `.yaml` が利用可能|
    |lms_url|`<lms_url>`|LMS のログイン URL||
    |selenium_executer|`<selenium_executer>`|selenium の executer への接続情報|例: `http://selenium-executer:4444/wd/hub`|

* 非必須パラメータ  

    |項目名|指定方法|概要|説明|
    |-|-|-|-|
    |browser|`-b <browser>`, `--browser <browser>`|テストを行うブラウザ|`selenium_executer` で処理可能なブラウザを指定する。`chrome`, `firefox` 等。指定しない場合は `chrome`|
    |headless|`--headless`|ヘッドレスモードの有効化|指定すると、ヘッドレスモードで実行する|
    |tool_id|`-i <tool_id>`, `--tool_id <tool_id>`|LMS 上の外部ツール ID|JupyterHub に LTI 連携でログインするための外部ツール ID。指定した場合は `course_name`, `tool_name` は不要|
    |course_name|`-c <course_name>`, `--course_name <course_name>`|対象コース名|`tool_id` を指定しない場合に必要。JupyterHub に LTI 連携でログインするための外部ツールを設定しているコース名|
    |tool_name|`-t <tool_name>`, `--tool_name <tool_name>`|対象外部ツール名|`tool_id` を指定しない場合に必要。JupyterHub に LTI 連携でログインするための外部ツール名|
    |src|`-s <src>`, `--src <src>`|single-user server 上で実行する処理ファイル|Notebook を開き、指定されたファイルの内容をそのままセルに記載して実行する。セルの実行結果は `selenium-client/result/*` に出力される|
    |notebook_name|`-n <notebook_name>`, `--notebook_name <notebook_name>`|`--src` 実行時に利用するノートブック名|既存ノートブックがあれば再利用し、存在しない場合は新規作成する|
    |output_result|`--output_result`|結果ファイルの出力|指定すると、selenium 実行結果ファイル（`selenium-client/result/*`）を出力する|
    |nologout|`--nologout`|ログアウト抑止|指定すると、テストユーザをテスト後にログアウトしない|
