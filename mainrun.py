""" Python3標準ライブラリ """
import json
import re
import os
import sys
import random
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


latest_data_dict: dict = dict()  # 最新のデータのみを格納する
device_dict: dict = dict()
is_window_shown: bool = False
is_continue_receive_send_data: bool = True

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
@eel.expose
def get_device_list():
    global device_dict
    device_dict = dict()
    eel.progress_manager("connection_list_update_started")  # type:ignore
    # self.device_list = {
    # '00:00:00:00:00:00': {'name': 'AAA', 'type': 'bluetooth', 'response': 'None'},
    # 'COM1': {'name': 'BBB', 'type': 'serial', 'response': 'None'},
    # }

    # Wired
    for device in list_ports.comports():
        temp_response = "Timeout"
        try:
            with serial.Serial(device.device, 9600, timeout=1) as con:
                temp_response = con.read(999999).decode("utf-8")  # 999999byteまで取得
        except serial.SerialException as error:
            temp_response = str(error)
        finally:
            temp = {"name": device.description, "type": "serial", "response": temp_response}
            eel.reload_connection_list({device.device: temp})  # type:ignore
            device_dict[device.device] = temp

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
            temp = {"name": device[1], "type": "bluetooth", "response": temp_response}
            eel.reload_connection_list({device[0]: temp})  # type:ignore
            device_dict[device[0]] = temp

    eel.progress_manager("connection_list_update_done")  # type:ignore

    return device_dict


def generate_dummy_data(dic):
    for key in dic.keys():
        dic[key] += int((random.random() * 10) - 5)
        dic[key] = max(0, dic[key])
    return dic


def receive_send_data():
    global latest_data_dict
    filename = f"store/indicators_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not IS_DISABLED_BACKGROUND_LOGGING:
        with open(filename, mode="a", encoding="UTF-8") as file:
            file.write("datetime," + ",".join(latest_data_dict.keys()) + "\n")
    while is_continue_receive_send_data:
        if IS_USE_DUMMY_DATA:
            latest_data_dict = generate_dummy_data(latest_data_dict)  # 一時的にデータを生成する
        eel.Data_PY2JS(latest_data_dict)  # type: ignore
        if not IS_DISABLED_BACKGROUND_LOGGING:
            with open(filename, mode="a", encoding="UTF-8") as file:
                file.write(str(dt.now()) + ",".join([str(num) for num in latest_data_dict.values()]) + "\n")
        eel.sleep(random.random() / 5)


# ---- データ処理関連ここまで ----


# ---- GUI生成関連 ----
def start_window():
    global is_window_shown
    is_window_shown = True
    eel.start("index.html", size=(1280, 720), mode="chrome", port=0, host="localhost", close_callback=after_closed_window, block=False)  # ポートを自動的に設定する
    eel.Get_Initial_Settings(INITIAL_SETTINGS)  # type: ignore

    update_connection_list_th = Thread(target=get_device_list)
    update_connection_list_th.start()


def after_closed_window(*args):  # type: ignore # pylint: disable=W0613
    global is_window_shown
    is_window_shown = False


def kill_entire_system():
    global is_continue_receive_send_data
    while True:
        if thread.is_alive():
            is_continue_receive_send_data = False
        else:
            sys.exit()


def continue_logging_and_exit():
    # ウィンドウ終了時にロギングを継続し、プログラムを終了するか尋ねる
    while True:
        eel.sleep(0.1)  # waitさせないとページにアクセスできない
        if IS_DISABLED_BACKGROUND_LOGGING and not is_window_shown:
            kill_entire_system()
        if not IS_DISABLED_BACKGROUND_LOGGING and not is_window_shown:
            input_character = input("ダッシュボードを閉じましたが、システムは稼働しています。\nシステム(Python)を終了する -> c\nもう一度ダッシュボードを開く -> o\n")
            if input_character == "c":
                kill_entire_system()
            elif input_character == "o":
                start_window()


# ---- GUI生成関連ここまで ----


# ---- その他関数類 ----
def load_JsonWithComment(path):
    with open(path, mode="r", encoding="UTF-8") as file:
        raw_text = file.read()
    text_comments_removed = re.sub(r"/\*[\s\S]*?\*/|//.*", "", raw_text)
    setting = json.loads(text_comments_removed)
    return setting


# ---- その他関数類ここまで ----

# ---- Args ----
print("Args:", sys.argv)
# --DisableBackGroundLogging : ログファイルの生成を停止する。デバッグ用
IS_DISABLED_BACKGROUND_LOGGING = "--DisableBackGroundLogging" in sys.argv
#
# --UseDummyData : ログファイルの生成を停止する。デバッグ用
IS_USE_DUMMY_DATA = "--UseDummyData" in sys.argv
#
# ---- Argsここまで ----

if __name__ == "__main__":
    # CSVファイルの保存先ディレクトリを生成
    if not os.path.exists(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"]):
        os.mkdir(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"])

    # eel.init("interface") # 起動時にかかる時間の82％が費やされる
    # allowed_extensions=["eel_js"]によって、起動時の処理時間を1~2秒短縮できる。
    # 内部ではinterfaceディレクトリの解析が行われており、余計なスクリプトファイルを除外して解析することによって処理時間が短縮される。
    # PythonでJavaScriptの関数を呼び出す前にinitを実行しないといけない
    eel.init("interface", allowed_extensions=["eel_js"])

    # load setting.json
    for k in INITIAL_SETTINGS["values"]["data_list"]:
        latest_data_dict[k] = 0  # 初期化

    # load settings.env.json
    if os.path.exists(PATH_PRIMARY_SETTINGS):
        antecedence_setting = load_JsonWithComment(PATH_PRIMARY_SETTINGS)
        INITIAL_SETTINGS["values"].update(antecedence_setting)

    thread = Thread(target=receive_send_data)
    thread.start()
    start_window()
    continue_logging_and_exit()
