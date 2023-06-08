# SolarCarSensorMonitor

## 利用方法

### 接続

1. マイコンとコンピューターを接続する。（Bluetooth を利用する場合、先に OS の設定から接続を行う。）
2. アプリケーションの接続先リストからマイコンを選択し、接続する。

### マイコン側の出力

`ValueName:Value\n`と出力することで、`ValueName`の値が`Value`であると送信できる。名前と数値の間は半角コロン`:`で区切る。`@\n`を送信することで、それまでに送信した値をグラフに反映できる。（このタイミングでログへの書き込みが行われる）

以下は、複数のセンサーから取得した値を`direction`として送信するユースケースである。

```cpp
// コード例
void setup() {
  Serial.begin(9600);
}

void loop() {
  // センサーから取得した値として使用する
  int thermal_sensor_value = 25;
  int direction_sensor_value = 180;
  int speed_sensor_value = 60;

  Serial.println("temperature:" + String(thermal_sensor_value));
  Serial.println("direction:" + String(direction_sensor_value));
  Serial.println("speed:" + String(speed_sensor_value));

  Serial.println("@"); // グラフ更新
  delay(1000);
}
```

## 環境

- Python 3.10.11
  - 少なくとも 3.7 以上のバージョンで開発してください。`dict`のキー順列が保証される仕様が必要です。
  - Anaconda など使わず、python.org からダウンロードするのが確実
- `requirement.txt`から仮想環境を作成し、実行することを推奨する。
- Chart.js 3.9.1
  - V3 以上にバージョンアップする場合、`interface/scripts/index.js`の（おそらく大規模な）改修が必須になる。
  - MIT ライセンス（ライセンス著作権表示必須、変形分布可）
    - github.com/chartjs/Chart.js/blob/master/LICENSE.md
- eel 0.16.0

## モジュールを追加でインストールする

- `.\.venv\Scripts\pip.exe install [module_name]`を実行する。
- 必須のモジュールにしたい場合は`requirements.txt`にも追加すること。

## EXE 化する方法

コンソールを非表示にするオプションは使用しないこと（標準入出力を利用する場面がある）

Python スクリプトとして実行するほうが望ましい。

### PyInstaller を使う

`\bats\Compile_asEXE.bat`を実行してください。

- `.\.venv\Scripts\python.exe -m eel mainrun.py interface --onefile --icon=interface/favicon.ico --clean --name=SolarCarSensorMonitor`を実行する。
  - `--onefile`：ひとつのファイルに纏める。圧縮が行われるため、容量が小さくなるが、起動に時間がかかる
  - `--icon=something.ico`：EXE ファイルのアイコンを指定する。ファイル形式は`.ico`のみ。
  - `--clean`：一時ファイルを削除
  - `--name=app_name`：EXE ファイルの名前を指定
- 簡単
- 比較的新しい Python に対応できる。
- 一般的にファイルが大容量になりやすい。（およそ 15MB）

### py2exe を使う（この環境では成功できたことがない）

- `.\.venv\Scripts\python.exe setup_py2exe.py py2exe`を実行する。
- Windows のみで実行できる。
- 一般的にファイルが軽量になりやすい。（およそ 20MB）
- コンパイル設定`setup_py2exe.py`を書く必要がある。

## トラブルシューティング

### `failed with KeyError`が発生する

```error:console
Traceback (most recent call last):
  File "src\\gevent\\greenlet.py", line 908, in gevent._gevent_cgreenlet.Greenlet.run
  File ".venv\lib\site-packages\eel\__init__.py", line 340, in _process_message
    _call_return_values[call_id] = message['value']
KeyError: 'value'
0000-00-00T00:00:00Z <Greenlet at **********: _process_message({'return': **********, 'status':
'error', 'e, <geventwebsocket.websocket.WebSocket object at 0x0)> failed with KeyError
```

- JavaScript において例外が発生している。Python 側では、例外でなく Warning として扱われる。
- Python から実行する場合、JavaScript において発生した例外は不明確に表示される（発生箇所や例外の内容は知ることができない）ため、デバッグには根気が求められる。該当しそうな箇所に`return;`を挿入し、それをずらしながらエラーの発生箇所を特定しなければならない。

### JavaScript 側の例外を詳細に分析する

上記の通り、通常の方法では JS 側で発生した例外を詳細に確認することができない。しかし、コードを以下のように記述すれば Web の開発者ツールを経由して詳細を確認することができる。ややコードが複雑になるが、単純なシンタックスエラーであれば、すぐに特定できるだろう。

```js:example
function exp(){
  try {
    /*
    すべての処理をこの中に含める（ここでエラーが発生する）
    throw new Error();
    */
  } catch (e) {
    console.log(e);
  }
}
// Error: Something Error
//     at <anonymous>:2:11
```

## 設定について

このシステムでは、インタフェースやデータ処理系での設定項目を Json ファイルによって行う。

- `./settings/settings.json`：基本的には、このファイルから設定を行う。
- `./settings/settings.env.json`：環境ごとに設定を変えるときには、このファイルから設定を行う。こちらで設定した内容が優先的に適応される。Git 管理から無視される。

### 設定項目

`./settings/settings.json`のコメントを参照

## プロファイリングする

コードの最適化を行うにあたって、処理時間が長い箇所を特定する必要がある。その為に必要なプロファイリングの方法をいかに述べる。

### cProfile を使う

VScode 環境であれば、`Profile:Launch Main Window`を実行することでプロファイリングを有効にした状態で、実行することができる。

以下のコマンドを実行すると、プロファイリング結果をブラウザで確認することができる。

```sh
.\.venv\Scripts\pip.exe install snakeviz
.\.venv\Scripts\python.exe -m snakeviz .\profile.prof
```

### LineProfiler を使う

Python ライブラリの LineProfiler を使う。直感的に処理時間を調べることができるものの、コードを改変しなければならない範囲が大きいため、注意が必要。
