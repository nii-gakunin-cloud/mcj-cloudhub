# 利用の流れ

## LMSからJupyterHubへログイン  

MCJ-CloudHubは、LMSのLTI認証利用が前提となっています。  
現在は Moodle 4.0 以降に対応しています。  

## ユーザ用のJupyter Notebook環境が起動する  

LMSで選択したコースにフォーカスした設定で環境が起動します。  
[DockerSpawner](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/spawner-types.html#dockerspawner)もしくは[SwarmSpawner](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/spawner-types.html#swarmspawner)を利用して、認証されたユーザ用の環境がDockerコンテナで起動します。  
nbgraderを利用する際に、受講するコースを選択する箇所がありますが、ここにはログイン時に選択していたコースのみが表示されます。  

## nbgraderで課題ファイルのやり取りと採点を行う  

詳細は、[nbgrader公式](https://nbgrader.readthedocs.io/en/stable/)をご覧ください。  
MCJ-CloudHubでの差分を以下に記載します。  

### nbgrader機能差分

- quickstartが使用不可  
    quickstartによって作成されるディレクトリや設定ファイルは、MCJ-CloudHubで設定している共通の設定により参照されないようになっているため、使用できません。

- 日本標準時（JST）以外への対応  
    日本標準時（JST）で使用することを前提としているため、変更できません。
