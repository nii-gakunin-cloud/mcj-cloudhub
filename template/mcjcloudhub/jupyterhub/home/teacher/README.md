# 課題ファイル管理（nbgrader）

[概要](#概要)  
[nbgrader の利用手順](#nbgrader-の利用手順)

## 概要

MCJ-CloudHub は、課題の配布・回収・採点に `nbgrader` を利用する前提で構成されています。
このページでは、教員が行う以下の操作を順番に説明します。

- 課題の作成
- 学生への配布
- 提出物の回収と採点
- 採点結果の返却
- LMS への成績送信

`nbgrader` では、各コースに 1 つ以上の課題を作成し、各課題に 1 つ以上のノートブックを含めます。
対象となるコースは、教員が Moodle から JupyterHub にログインしたときに選択していたコースです。

【階層イメージ】
```
コース
  ∟ 課題
      ∟ ファイル群
```

## nbgrader の利用手順

### 1. 課題を作成する

1. `Formgrader` 画面を開きます。

    - Classic Notebook View の場合は、画面上部の `Formgrader` タブを開きます。
    - JupyterLab View の場合は、ツールバーの `Nbgrader` から `Formgrader` を開きます。

2. `Add new assignment...` をクリックし、課題名と締め切り日時を入力します。

    課題を作成すると、`Formgrader` 画面のテーブルに課題が追加されます。
    追加された課題名をクリックすると、その課題用ノートブックを作成するディレクトリが開きます。

    締め切り日時の設定は任意です。
    設定した場合は、提出の遅れに応じて減点する設定が可能です。[^1]

    [^1]: 参考: [Late submission plugin](https://nbgrader.readthedocs.io/en/0.8.x/plugins/late-plugin.html)

3. 課題ファイルとして配布するノートブックを作成します。

    `Formgrader` 画面で課題名をクリックし、課題用ノートブックの作成先ディレクトリを開いて、学生に配布するノートブックを作成します。  
    自動採点を行う場合は、対象セルに `nbgrader` 用の設定を追加する必要があります。  
    詳細は [Creating and grading assignments](https://nbgrader.readthedocs.io/en/0.8.x/user_guide/creating_and_grading_assignments.html) を参照してください。  

    リリースした課題について学生の実行履歴を分析する場合は、Notebook 実行時に `LC_wrapper` 対応カーネルを利用してください。  
    MCJ-CloudHub 標準の Jupyter コンテナイメージに含まれる `Python 3` カーネルでは、`LC_wrapper` が有効です。  
    詳細は `teacher_tools/log_analyze/README.md` を参照してください。

### 2. 学生に課題を配布する

課題作成後は、学生向けファイルを生成し、配布状態にする必要があります。

1. 配布用ファイルを生成します。

    `Formgrader` 画面の `Generate` 列にあるアイコンをクリックすると、学生向けに加工されたノートブックが生成されます。

    `nbgrader` では、教員用ノートブックから学生配布用ノートブックを自動生成できます。
    たとえば、`### BEGIN SOLUTION` などの特定マーカーで囲まれた箇所は、学生用ノートブックでは解答欄に置き換えられます。[^2]
    これにより、教員用ノートブックに模範解答を保持したまま、学生には空欄の状態で配布できます。

    [^2]: 参考: [`BEGIN SOLUTION`等のタグ](https://nbgrader.readthedocs.io/en/latest/configuration/student_version.html#autograded-answer-cells)

2. 課題を配布します。

    `Formgrader` 画面の `Release` 列にあるアイコンをクリックすると、課題ファイル一式が学生に配布されます。
    学生はこの時点から課題をダウンロードし、提出できます。

    学生は何度でも再提出できます。
    教員が回収した時点での最新提出物が採点対象になります。

### 3. 提出物を回収して採点する

1. 提出物を回収します。

    `Formgrader` 画面の `Collect` 列にあるアイコンをクリックすると、提出済み課題を回収できます。

2. 提出物を採点します。

    課題を回収した後、`Submissions` 列に表示される数字をクリックすると、提出物一覧を開けます。
    採点は通常、自動採点を先に行い、その後に手動採点を行います。

    画面には `Need Autograding` などの案内が表示されるため、それに従って処理を進めてください。
    手動採点では、各セルへのコメント追加や任意の加点も行えます。

### 4. 採点結果を返却する

1. フィードバックを生成して返却します。

    自動採点結果、手動採点結果、コメントを集計した HTML ファイルを学生ごとに生成します。
    採点が完了したら、`Formgrader` 画面の `Generate Feedback` 列にあるアイコンをクリックして HTML ファイルを生成してください。

    生成後、`Release Feedback` 列のアイコンをクリックすると、各学生へフィードバックを配布できます。
