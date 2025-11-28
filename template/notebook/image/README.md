# Single-user notebook serverコンテナイメージ

## イメージ一覧  

以下の各イメージが、本ディレクトリ内の同名のディレクトリに対応しています。


### notebook-7.5.0（default）  

- ベースイメージ
    - [quay.io/jupyter/scipy-notebook:notebook-7.5.0](https://quay.io/repository/jupyter/scipy-notebook/manifest/sha256:234da96996f255d9f6b63b880ff41e8537865b96f2f07707b35b59e830199a2d)
        - `notebook==7.5.0`
        - `jupyterlab==4.5.0`
- 実行ログ収集のためのライブラリがインストール済  
    - [LC_wrapper](https://github.com/NII-cloud-operation/Jupyter-LC_wrapper?tab=readme-ov-file)
    - [LC_nblineage](https://github.com/NII-cloud-operation/Jupyter-LC_nblineage)

### notebook-6.5.4
- ベースイメージ
    - [jupyter/scipy-notebook:notebook-6.5.4](https://hub.docker.com/layers/jupyter/scipy-notebook/notebook-6.5.4/images/sha256-bf491591501d413c481cb32a48feed29dc09ad6b6f49dedc1f411dd5cb618758?context=explore)
        - `notebook==6.5.4`
        - `jupyterlab==3.6.7`
- 実行ログ収集のためのライブラリがインストール済  
    ※注 JupyterLabには一部対応していない機能があるため、`Classic Notebook` UIでの実行を推奨。
    - [LC_wrapper](https://github.com/NII-cloud-operation/Jupyter-LC_wrapper?tab=readme-ov-file)
    - [LC_nblineage](https://github.com/NII-cloud-operation/Jupyter-LC_nblineage)
    - [Jupyter-multi_outputs](https://github.com/NII-cloud-operation/Jupyter-multi_outputs)
