# 開発者向け

## ドキュメント生成

[zensical](https://zensical.org/)を利用してドキュメントをビルドします。  

### 対象ファイル収集

以下を実行すると、サブディレクトリに散らばっている`README.md`と、`docs`ディレクトリに保存している全体向けドキュメントを１つのディレクトリに収集します。

```
python tools/generate_docs_from_readmes.py
```

!!! note

    - 対象外ディレクトリの指定: `tools/generate_docs_from_readmes.py` にて、`README.md` 収集の対象外とするディレクトリを指定しています。
    - `zensical.toml` の生成: ファイルの追加・削除がある場合など、収集したファイルを基に `zensical.toml` を自動作成するには `--update_config` を指定してください。

      この場合、ドキュメントの目次は各マークダウンファイルの先頭行になります。目次名を変更する場合は、生成される `zensical.toml` を編集してください。

      目次の順序は生成時に指定できないため、必要に応じて手動で変更してください。

### ドキュメントのビルドと、プレビュー用サーバの起動  

以下を実行すると、[zensicalコンテナ](https://hub.docker.com/r/zensical/zensical)でドキュメントのビルドと、プレビュー用サーバの起動を行います。  
ポートなどの設定は、適宜変更してください。  

```
docker run --rm -it -p 8000:8000 -v ${PWD}/zensical.toml:/docs/zensical.toml -v ${PWD}/docmerged:/docs/docmerged zensical/zensical
```
