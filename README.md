# SolarCarSensorMonitor

## 環境

- Python 3.10.11
  - Anaconda など使わず、python.org からダウンロードするのが確実
- `requirement.txt`から仮想環境を作成し、実行することを推奨する
- Chart.js 3.9.1
  - V3 以上にバージョンアップする場合、`interface/scripts/index.js`の（おそらく大規模な）改修が必須
  - MIT ライセンス（ライセンス著作権表示必須、変形分布可）
    - github.com/chartjs/Chart.js/blob/master/LICENSE.md
- eel 0.16.0

## モジュールを追加でインストールする

- `.\.venv\Scripts\pip.exe install [module_name]`を実行する
- 必須のモジュールにしたい場合は`requirements.txt`にも追加すること

## EXE 化する方法

コンソールを非表示にするオプションは使用しないこと（標準入出力を利用する場面がある）

Python スクリプトとして実行するほうが望ましい

### PyInstaller を使う

- `.\.venv\Scripts\python.exe -m eel mainrun.py interface --onefile --icon=interface/favicon.ico --clean --name=SolarCarSensorMonitor`を実行する
  - `--onefile`：ひとつのファイルに纏める
  - `--icon=something.ico`：EXE ファイルのアイコンを指定
  - `--clean`：一時ファイルを削除
  - `--name=app_name`：EXE ファイルの名前を指定
- 簡単
- 比較的新しい Python に対応できる
- 一般的にファイルが大容量になりやすい（およそ 15MB）

### py2exe を使う（この環境では成功できたことがない）

- `.\.venv\Scripts\python.exe setup_py2exe.py py2exe`を実行する
- Windows のみで実行できる
- 一般的にファイルが軽量になりやすい（およそ 20MB）
- コンパイル設定`setup_py2exe.py`を書く必要がある
