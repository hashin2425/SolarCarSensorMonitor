""" Python3標準ライブラリ """
import json
import re
import os
import sys
import random
import warnings
import tracemalloc
from datetime import datetime as dt
from threading import Thread

# https://pypi.org/project/Eel/
# https://qiita.com/inoory/items/f431c581332c8d500a3b
# pip install Eel
import eel  # 起動時にかかる時間の16％が費やされている


# https://pypi.org/project/pybluez2/
# pip install pybluez2
import bluetooth


# https://pypi.org/project/pyserial/
# pip install pyserial
import serial
from serial.tools import list_ports
from serial.serialutil import SerialException


latest_data_dict: dict = dict()  # 最新のデータのみを格納する
device_dict: dict = dict()
is_window_shown: bool = False
is_continue_receive_send_data: bool = True
main_connection = None
logging_filename: str = ""

# ---- 設定項目 ----
PATH_PRIMARY_SETTINGS = "./settings.env.json"
INITIAL_SETTINGS = {
    "description": {
        "interface": {
            "update_interval_sec": "グラフの描画間隔を指定します。数値を小さくすると、高頻度に更新されますが、端末の負荷が上昇します。単位は秒。",
            "graph_max_display": "グラフに表示するデータの数を指定します。単位は件数。",
            "dark_mode": "起動時のダークモードの有効/無効を指定します。",
        },
        "data_logging": {
            "data_log_dir": "ロギングの保存先ファイル名を指定します。ソフトウェアのexeが存在するディレクトリ上にファイルを生成します。",
            "data_log_filename": "ロギングによって生成されたファイルの接頭辞を指定します。日時と拡張子が自動的に補完されます。例：log_20220101_1010.csv",
        },
    },
    "values": {
        "interface": {
            "update_interval_sec": 0.1,
            "graph_max_display": 100,
            "dark_mode": False,
        },
        "data_logging": {"data_log_dir": "store", "data_log_filename": "log"},
        "data_list": {
            "battery_v": {"display_name": "バッテリー電圧", "unit": "V", "safe_range_min": -10000, "safe_range_max": 10000},
            "battery_a": {"display_name": "バッテリー残量", "unit": "A", "safe_range_min": 0, "safe_range_max": 2},
            "battery_temp": {"display_name": "バッテリー温度", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000},
            "body_temp": {"display_name": "機体温度", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000},
            "speed": {"display_name": "速度", "unit": "km/h", "safe_range_min": -10000, "safe_range_max": 10000},
            "accelerator": {"display_name": "アクセル", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000},
            "break": {"display_name": "ブレーキ", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000},
        },
    },
}
# ---- 設定項目ここまで ----


# ---- データ処理関連 ----
class Connection:
    """
    シリアルまたはBluetoothを介したデバイスへの接続を表すクラス。

    Attributes:
        connection_serial (serial.Serial): シリアル接続オブジェクト。Serial接続の場合のみ。
        connection_bluetooth (bluetooth.BluetoothSocket): Bluetooth接続オブジェクト。Bluetooth接続の場合のみ。
        connect_to_id (str): 接続先デバイスのID。
        connection_type (str): 接続の種類（"Serial"または"Bluetooth"）。
        text_received (str): デバイスから受信したテキスト。
        is_enabled_connection (bool): 接続が有効かどうかを示すフラグ。

    Methods:
        __init__(self, _connect_to_id: str) -> None:
            Connectionクラスの新しいインスタンスを初期化し、指定されたデバイスに接続を確立します。
        kill_connection(self) -> None:
            デバイスへの接続を閉じ、接続観察スレッドを停止します。
        connection_observer(self):
            別のスレッドで実行され、接続からデータを継続的に読み取るメソッドです。
    """

    connection_serial: serial.Serial
    connection_bluetooth: bluetooth.BluetoothSocket
    connect_to_id: str = "None"
    connection_type: str = "None"
    received_text: str = ""
    is_enabled_connection: bool = True

    def __init__(self, _connect_to_id: str) -> None:
        self.connect_to_id = _connect_to_id
        if self.connect_to_id not in device_dict:
            print(f"デバイスが見つかりません。：{self.connect_to_id}")
            return
        # DummyConnection
        if device_dict[self.connect_to_id]["type"] == "DummyPort":
            self.connection_type = "DummyPort"
        # Serial
        if device_dict[self.connect_to_id]["type"] == "Serial":
            self.connection_type = "Serial"
            self.connection_serial = serial.Serial(self.connect_to_id, 9600, timeout=1)
        # Bluetooth
        elif device_dict[self.connect_to_id]["type"] == "Bluetooth":
            self.connection_type = "Bluetooth"
            self.connection_bluetooth = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # type:ignore
            self.connection_bluetooth.connect((self.connect_to_id, 1))
        # 通信開始
        self.thread_receive_data = Thread(target=self.connection_observer)
        self.thread_receive_data.start()
        device_dict[self.connect_to_id]["connected"] = True
        _print(device_dict[self.connect_to_id])
        # デバイス一覧に反映
        eel.reload_connection_list({self.connect_to_id: device_dict[self.connect_to_id]}, True)  # type:ignore
        for key, dic in device_dict.items():
            if key != self.connect_to_id:
                eel.reload_connection_list({key: dic}, False)  # type:ignore
        eel.add_remove_notification(True, "CONNECTION_ESTABLISHED", "C", "接続が成功しました。")  # type: ignore

    def kill_connection(self) -> None:
        self.is_enabled_connection = False
        self.thread_receive_data.join()
        device_dict[self.connect_to_id]["connected"] = False
        # Serial
        if self.connection_type == "Serial":
            self.connection_serial.close()
        # Bluetooth
        elif self.connection_type == "Bluetooth":
            self.connection_bluetooth.close()
        eel.add_remove_notification(False, "CONNECTION_ESTABLISHED", "C", "接続が成功しました。")  # type: ignore

    def connection_observer(self) -> None:
        """
        Observes the connection and receives data from the device. If using dummy data,
        generates random data. If using serial or bluetooth, reads data from the connection.
        Parses the received text and updates the latest data dictionary.

        Returns:
            None
        """
        SEPARATE_NAME_VALUE = ":"
        SEPARATE_VALUE_VALUE = "#"
        SEPARATE_EACH_UPDATE = "@"

        while self.is_enabled_connection:
            eel.sleep(0.05)
            data = ""

            # Get the latest data
            if self.connection_type == "DummyPort":
                # If using dummy data, generate random data
                eel.sleep(random.random() / 5)
                for key in latest_data_dict:
                    latest_data_dict[key] = max(0, latest_data_dict[key] + int((random.random() * 10) - 5))
                data = SEPARATE_VALUE_VALUE.join([f"{key}{SEPARATE_NAME_VALUE}{value}" for key, value in latest_data_dict.items()]) + SEPARATE_VALUE_VALUE + SEPARATE_EACH_UPDATE
            elif self.connection_type == "Serial":
                # If using serial, read data from the connection
                data = self.connection_serial.read(999999).decode("utf-8")  # Up to 999999 bytes # Takes about 0.5-1 sec to process?
            elif self.connection_type == "Bluetooth":
                # If using bluetooth, read data from the connection
                data = self.connection_bluetooth.recv(1024).decode("utf-8")

            # Send the data
            if len(data) > 0:
                self.received_text += data.replace("\r", "").replace("\n", "#")
                _print(self.received_text)

            if SEPARATE_EACH_UPDATE in self.received_text:
                # Parse the received text
                parsed_text = [dict([x.split(SEPARATE_NAME_VALUE) for x in y.split(SEPARATE_VALUE_VALUE) if SEPARATE_NAME_VALUE in x]) for y in self.received_text.split(SEPARATE_EACH_UPDATE)]
                _print(parsed_text)
                if len(parsed_text) > 0:
                    # Update the latest data dictionary
                    new_data_dict = {key: int(value) for key, value in parsed_text[0].items()}
                    _print(new_data_dict)
                    latest_data_dict.update(new_data_dict)
                    eel.Data_PY2JS(latest_data_dict)  # type: ignore
                    _print(latest_data_dict)

                    if not IS_DISABLED_BACKGROUND_LOGGING:
                        # Log the latest data
                        with open(logging_filename, mode="a", encoding="UTF-8") as file:
                            new_line = str(dt.now()) + ",".join([str(num) for num in latest_data_dict.values()]) + "\n"
                            file.write(new_line)
                self.received_text = ""


@eel.expose
def connect_device(device_name: str):
    global main_connection
    if isinstance(main_connection, Connection):
        # すでに接続が確立している場合、切断する
        _print(main_connection)
        main_connection.kill_connection()
        main_connection = None
    if device_name != "**disconnect**":
        # **disconnect**で切断する(別デバイスへの再接続をしない)
        main_connection = Connection(device_name)
    else:
        # デバイスリストに反映
        for i, key in enumerate(device_dict.keys()):
            eel.reload_connection_list({key: device_dict[key]}, i == 0)  # type:ignore


def create_new_logging_file() -> None:
    global logging_filename
    dir_name = INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"]
    prefix = INITIAL_SETTINGS["values"]["data_logging"]["data_log_filename"]
    logging_filename = f"{dir_name}/{prefix}_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(logging_filename, mode="a", encoding="UTF-8") as file:
        file.write("datetime," + ",".join(latest_data_dict.keys()) + "\n")


@eel.expose
def get_device_list():
    # self.device_list = {
    # '00:00:00:00:00:00': {'name': 'AAA', 'type': 'bluetooth', 'response': 'None', 'connected': False},
    # 'COM1': {'name': 'BBB', 'type': 'serial', 'response': 'None', 'connected': False},
    # }
    global device_dict

    # 現在接続されているポートの情報を残す
    now_connection_id = ""
    if isinstance(main_connection, Connection):
        now_connection_id = main_connection.connect_to_id
    device_dict = dict()

    eel.progress_manager("connection_list_update_started")  # type:ignore

    # DummyConnection
    if IS_USE_DUMMY_DATA:
        temp = {"DUMMY_PORT": {"name": "デバッグ用ダミーポート", "type": "DummyPort", "response": "This is dummy connection.", "connected": "DUMMY_PORT" == now_connection_id}}
        eel.reload_connection_list(temp)  # type:ignore
        device_dict = device_dict | temp
    # Wired
    for device in list_ports.comports():
        temp_response = "Timeout"
        try:
            with serial.Serial(device.device, 9600, timeout=1) as con:
                temp_response = con.read(999999).decode("utf-8")  # 999999byteまで取得
        except (serial.SerialException, SerialException, KeyError, AttributeError) as error:
            temp_response = str(error)
        finally:
            temp = {device.device: {"name": device.description, "type": "Serial", "response": temp_response, "connected": device.device == now_connection_id}}
            eel.reload_connection_list(temp)  # type:ignore
            device_dict = device_dict | temp

    # Bluetooth
    for device in bluetooth.discover_devices(lookup_names=True, lookup_class=False):  # ここで10秒くらいかかる
        temp_response = "Timeout"
        try:
            with bluetooth.BluetoothSocket(bluetooth.RFCOMM) as con:  # type: ignore
                con.connect((device[0], 1))
                temp_response = con.recv(1024).decode("utf-8")
        except (bluetooth.BluetoothError, AttributeError, KeyError) as error:
            temp_response = str(error)
        finally:
            temp = {device[0]: {"name": device[1], "type": "Bluetooth", "response": temp_response, "connected": device[0] == now_connection_id}}
            eel.reload_connection_list(temp)  # type:ignore
            device_dict = device_dict | temp

    eel.progress_manager("connection_list_update_done")  # type:ignore


# ---- データ処理関連ここまで ----


# ---- GUI生成関連 ----
@eel.expose
def window_initialize():
    # Windowの起動が完了した段階でJS側から呼び出す
    # Python側の設定(INITIAL_SETTINGS)をJSに送信する
    _ = eel.Get_Initial_Settings(INITIAL_SETTINGS)()  # type:ignore


def start_window():
    global is_window_shown
    is_window_shown = True
    eel.start("index.html", size=(1280, 720), mode="chrome", port=0, host="localhost", close_callback=after_closed_window, block=False)  # ポートを自動的に設定する

    update_connection_list_th = Thread(target=get_device_list)
    update_connection_list_th.start()


def after_closed_window(*args):  # type: ignore # pylint: disable=W0613
    global is_window_shown
    is_window_shown = False


def kill_entire_system():
    print("すべてのシステムを終了します。")
    connect_device("**disconnect**")
    sys.exit()


def continue_logging_and_exit():
    # ウィンドウ終了時にロギングを継続し、プログラムを終了するか尋ねる
    while True:
        eel.sleep(0.1)  # waitさせないとページにアクセスできない
        if IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED and not is_window_shown:
            kill_entire_system()
        if not IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED and not is_window_shown:
            input_character = input("ダッシュボードを閉じましたが、システムは稼働しています。\nバックエンドシステム(Python)を終了する -> close\nもう一度ダッシュボードを開く -> open\n> ")
            if input_character == "close":
                kill_entire_system()
            elif input_character == "open":
                _print(00)
                start_window()
                _print(11)


def window_alive_check():
    while True:
        eel.sleep(0.01)  # waitさせないとページにアクセスできない
        eel.window_alive_check()  # type: ignore


# ---- GUI生成関連ここまで ----


# ---- その他関数類 ----
def load_JsonWithComment(path):
    with open(path, mode="r", encoding="UTF-8") as file:
        raw_text = file.read()
    text_comments_removed = re.sub(r"/\*[\s\S]*?\*/|//.*", "", raw_text)
    setting = json.loads(text_comments_removed)
    return setting


@eel.expose
def _print(*args):
    # デバッグ用
    if DEBUG_PRINT_MODE:
        print(dt.now(), ":", *args)


# ---- その他関数類ここまで ----

# eel.init("interface") # 起動時にかかる時間の82％が費やされる
# allowed_extensions=["eel_js"]によって、起動時の処理時間を1~2秒短縮できる。
# 内部ではinterfaceディレクトリの解析が行われており、余計なスクリプトファイルを除外して解析することによって処理時間が短縮される。
# PythonでJavaScriptの関数を呼び出す前にinitを実行しないといけない
eel.init("interface", allowed_extensions=["eel_js"])

# ---- Args ----
# --DisableBackGroundLogging : ログファイルの生成を停止する。デバッグ用
IS_DISABLED_BACKGROUND_LOGGING = "--DisableBackGroundLogging" in sys.argv
eel.add_remove_notification(IS_DISABLED_BACKGROUND_LOGGING, "IS_DISABLED_BACKGROUND_LOGGING", "L", "[デバッグ機能]ログファイルの生成が停止されています。")  # type: ignore
#
# --ClosePythonWhenWindowClosed : ウィンドウを閉じる時にPythonを終了する
IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED = "--ClosePythonWhenWindowClosed" in sys.argv
eel.add_remove_notification(IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED, "IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED", "C", "[デバッグ機能]ウィンドウ終了時に、バックエンドシステムが終了されます。")  # type: ignore
#
# --UseDummyData : ダミーのデバイスを利用できる。デバッグ用
IS_USE_DUMMY_DATA = "--UseDummyData" in sys.argv
eel.add_remove_notification(IS_USE_DUMMY_DATA, "IS_USE_DUMMY_DATA", "D", "[デバッグ機能]ダミーデバイスが有効です。")  # type: ignore
#
# --DebugPrint : デバッグモード有効時にのみPrintする。デバッグ用
DEBUG_PRINT_MODE = "--DebugPrint" in sys.argv
eel.add_remove_notification(DEBUG_PRINT_MODE, "DEBUG_PRINT_MODE", "P", "[デバッグ機能]デバッグ情報がコンソールに出力されます。")  # type: ignore
if not DEBUG_PRINT_MODE:
    # エラーや警告を非表示
    warnings.simplefilter("ignore")
else:
    # エラーや警告をすべて表示
    tracemalloc.start()
    warnings.resetwarnings()
#
os.system("cls")
_print("Args:", sys.argv)
# ---- Argsここまで ----

if __name__ == "__main__":
    # CSVファイルの保存先ディレクトリを生成
    if not os.path.exists(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"]):
        os.mkdir(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"])

    # load setting.json
    for k in INITIAL_SETTINGS["values"]["data_list"]:
        latest_data_dict[k] = 0  # 初期化

    # load settings.env.json
    if os.path.exists(PATH_PRIMARY_SETTINGS):
        antecedence_setting = load_JsonWithComment(PATH_PRIMARY_SETTINGS)
        INITIAL_SETTINGS["values"].update(antecedence_setting)

    thread = Thread(target=window_alive_check, daemon=True)
    thread.start()

    start_window()
    continue_logging_and_exit()
