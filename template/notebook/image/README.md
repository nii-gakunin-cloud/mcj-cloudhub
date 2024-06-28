# Single-user notebook serverコンテナイメージ

## イメージ一覧
以下の各イメージが、本ディレクトリ内の同名のディレクトリに対応しています。

### notebook-6.5.4
- ベースイメージ
    - [jupyter/scipy-notebook:notebook-6.5.4](https://hub.docker.com/layers/jupyter/scipy-notebook/notebook-6.5.4/images/sha256-bf491591501d413c481cb32a48feed29dc09ad6b6f49dedc1f411dd5cb618758?context=explore)
    - labは`3.6.7`
- 実行ログ収集のためのライブラリがインストールされている  
    ※注 JupyterLabには一部対応していない機能があるため、`Classic Notebook` UIでの実行を推奨。
    - [LC_wrapper](https://github.com/NII-cloud-operation/Jupyter-LC_wrapper?tab=readme-ov-file)
    - [LC_nblineage](https://github.com/NII-cloud-operation/Jupyter-LC_nblineage)
    - [Jupyter-multi_outputs](https://github.com/NII-cloud-operation/Jupyter-multi_outputs)

### notebook-7
- ベースイメージ
    - [jupyter/scipy-notebook:notebook-7.0.4](https://hub.docker.com/layers/jupyter/scipy-notebook/notebook-7.0.4/images/sha256-c27585e6eabd2e7d96921cf252fefaab468b435efe74b15749c55a4f97a40365?context=explore)
    - [jupyter/scipy-notebook:lab-4.0.6](https://hub.docker.com/layers/jupyter/scipy-notebook/lab-4.0.6/images/sha256-c27585e6eabd2e7d96921cf252fefaab468b435efe74b15749c55a4f97a40365?context=explore)
