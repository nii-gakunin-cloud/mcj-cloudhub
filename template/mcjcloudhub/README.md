# 環境構築

## 本番環境セットアップ

### 前提

環境構築のために必要なものは以下の通りです。  

- Jupyterhub用のマシン
    - managerノード用（必須）
        - 外部からアクセス可能であること
        - httpsでの通信にのみ対応しているため、ドメインの取得が必須
    - workerノード用（0以上）
        - 各ユーザ用のコンテナが起動するノード
        - 検証用途などの場合、managerノードで兼ねることも可能
- Moodleが利用可能であること  
    - [MCJ-CloudHub](https://github.com/nii-gakunin-cloud/mcj-cloudhub)はMoodleのLTI1.3認証の利用を前提としています
    - [MCJ-CloudHub](https://github.com/nii-gakunin-cloud/mcj-cloudhub)用の外部ツールの作成が必要です


### 構成

- 全体

![](./images/arch-readme.png)

- managerノード上のコンテナ

|コンテナ名|設定内容|
|-|-|
|JupyterHub|Jupyterhubコンテナ|
|MariaDB|Jupyterhub用のDB|
|OpenLDAP|Jupyterhubユーザ管理用のLDAPサーバ|
|Nginx|Jupyterhubへのアクセスを中継するプロキシサーバ（SSL/TLS終端）|
|configurable-http-prozy|Jupyterhub管理のプロキシサーバ|

### 構築作業

[MCJ-CloudHub](https://github.com/nii-gakunin-cloud/mcj-cloudhub)は、[学認クラウドオンデマンド構築サービス（OCS）](https://cloud.gakunin.jp/ocs/)上に構築するアプリケーションテンプレートとして公開しています。  
前提として、[VCコントローラ](https://nii-gakunin-cloud.github.io/ocs-docs/usermanual/#vc%E3%82%B3%E3%83%B3%E3%83%88%E3%83%AD%E3%83%BC%E3%83%A9)を利用するための環境が必要です。  
自身で[VCコントローラ](https://nii-gakunin-cloud.github.io/ocs-docs/usermanual/#vc%E3%82%B3%E3%83%B3%E3%83%88%E3%83%AD%E3%83%BC%E3%83%A9)のセットアップを行う場合は、[ポータブル版VCコントローラ](https://github.com/nii-gakunin-cloud/ocs-vcp-portable)を利用できます。  
[学認クラウドオンデマンド構築サービス（OCS）](https://cloud.gakunin.jp/ocs/)のテンプレートとして[MCJ-CloudHub](https://github.com/nii-gakunin-cloud/mcj-cloudhub)をセットアップする場合、そちらのテンプレート利用マニュアルを参照し、構築作業を行ってください。  

## 開発環境セットアップ

MoodleとJupyterhubを同じマシン上に起動します。

まず、開発環境用のセットアップを行います。  

```
make devsetup
```

`.env`ファイルが作成されます。  
Moodleのログインパスワードなどを変更する場合は、手動で編集してください。  

コンテナを起動します。  

```
make devup
```

3分ほどで、JupyterhubとMoodleが起動します。  
Moodleが起動したらブラウザでアクセスし、ログインします。  

URL: <https://localhost/moodle/>  
ID: `admin` PW: `changethis`（`.env`に記載）

`サイト管理 > プラグイン > 活動モジュール > 外部ツール > ツールを管理する` と進み、ツールの手動設定画面を開きます。  

|項目名|設定内容|
|-|-|
|`ツール名`|任意のツール名|
|`ツールURL`|`https://localhost`|
|`LTIバージョン`|`LTI 1.3`|
|`公開鍵タイプ`|`RSAキー`|
|`公開鍵`|`mcj-data/secrets/lti_pubkey.pem` の内容|
|`ログイン開始URL`|`https://localhost/hub/lti13/oauth_login`|
|`リダイレクトURI`|`https://localhost/hub/lti13/oauth_callback`|
|`ツール設定使用`|`活動チューザまたは事前設定ツールに表示する`|
|`デフォルト起動コンテナ`|`新しいウィンドウ`|
|`サービス`>`IMS LTI課題および評定サービス`|`このサービスを評定同期およびカラム管理に使用する`(AGS用)|
|`サービス`>`IMS LTI氏名およびロールプロビジョニング`|`このサービスをプライバシー設定を基にメンバシップ情報を検索するため使用します`(NRPS用)|
|`プライバシー`>`ランチャ名をツールと共有する`|`常に`|
|`プライバシー`>`ツールからの評定を受け付ける`|`常に`|

必要事項を入力後、ツールを作成すると、ツール一覧に追加されます。  
追加されたツールの虫眼鏡アイコンから、以下の項目を確認し、`.env`ファイルに記載します。  

<details>
<summary>ツール情報の場所</summary>

<img src="../../images/mdl_outer_tools.png" alt="Moodle の外部ツール一覧画面">
<img src="../../images/mdl_outer_tool_info.png" alt="Moodle の外部ツール情報画面">

</details>

|Moodle上の項目名|`.env`での項目名|
|-|-|
|プラットフォームID|LMS_PLATFORM_ID|
|クライアントID|LMS_CLIENT_ID|

`.env`ファイル編集後、jupyterhubで読み込むために、jupyterhubコンテナを再起動します。  

```
make devrestartjh
```

Moodleにてコース作成・設定を行うことで、Jupyterhubにログイン可能となります。  

1. コース作成
1. 作成したコースでの、外部ツール利用設定
1. 設定した外部ツールからJupyterhubにログイン


## オプショナル項目

Jupyterhubの設定を環境変数経由で行うことが出来ます。  
以下、JupyterHubコンテナに設定可能な環境変数のうち、代表的なものを示します。  
※その他の項目については、`jupyterhub_config.py`を参照してください。  

|環境変数|効果|デフォルト|
|-|-|-|
|JUPYTERHUB_ADMIN_USERS|Jupyterhubの管理者権限を持たせるユーザ（リスト）|""|
|ENABLE_CUSTOM_SETUP|'yes'を指定することで、教師ユーザが、コース内の学生の環境が起動する際に実行する任意のスクリプト（`*.sh`）を設定可能とする|無効|
