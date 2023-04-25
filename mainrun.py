import eel
# https://pypi.org/project/Eel/
# https://qiita.com/inoory/items/f431c581332c8d500a3b
# pip install Eel

import bluetooth
# https://pypi.org/project/pybluez2/
# pip install pybluez2

import serial
from serial.tools import list_ports
# https://pypi.org/project/pyserial/
# pip install pyserial

# Python3標準ライブラリ
import json
import re
import os
import sys
import random
from math import sin
from time import sleep, time
from datetime import datetime as dt
from threading import Thread

latest_data_dict = dict() # 最新のデータのみを格納する
is_window_shown = False
is_continue_receive_send_data = True
path_antecedence_settings = "./settings.env.json"
device_list = dict()

# ---- 設定項目 ----
initial_settings = {
    "description":{
        "interface": {
            "update_interval_sec":"グラフの描画間隔を指定します。数値を小さくすると、高頻度に更新されますが、端末の負荷が上昇します。単位は秒。",
            "graph_max_display":"グラフに表示するデータの数を指定します。単位は件数。",
            "dark_mode":"起動時のダークモードの有効/無効を指定します。",
        },
        "data_logging": {
            "data_log_dir": "ロギングの保存先ファイル名を指定します。ソフトウェアのexeが存在するディレクトリ上にファイルを生成します。",
            "data_log_filename": "ロギングによって生成されたファイルの接頭辞を指定します。日時と拡張子が自動的に補完されます。例：log_20220101_1010.csv",
        }
    },    "values":{
    "interface": {
        "update_interval_sec": 0.1,
        "graph_max_display": 100,
        "dark_mode": False,
    },
    "data_logging": {
        "data_log_dir": "store",
        "data_log_filename": "log"
    },
    "data_list": {
        "battery_v": {
            "display_name": "バッテリー電圧",
            "unit": "V",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        },
        "battery_a": {
            "display_name": "バッテリー残量",
            "unit": "A",
            "safe_range_min": 0,
            "safe_range_max": 2
        },
        "battery_temp": {
            "display_name": "バッテリー温度",
            "unit": "℃",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        },
        "body_temp": {
            "display_name": "機体温度",
            "unit": "℃",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        },
        "speed": {
            "display_name": "速度",
            "unit": "km/h",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        },
        "accelerator": {
            "display_name": "アクセル",
            "unit": "%",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        },
        "break": {
            "display_name": "ブレーキ",
            "unit": "%",
            "safe_range_min": -10000,
            "safe_range_max": 10000
        }
    }
}}
# ---- 設定項目ここまで ----

# ---- データ処理関連 ----
@eel.expose
def get_device_list():
    global device_list
    device_list = dict()
    eel.progress_manager("connection_list_update_started") # type:ignore
    # self.device_list = {
    # '00:00:00:00:00:00': {'name': 'AAA', 'type': 'bluetooth', 'response': 'None'},
    # 'COM1': {'name': 'BBB', 'type': 'serial', 'response': 'None'},
    # }

    # Wired
    for device in list_ports.comports():
        temp_response = "Timeout"
        try:
            with serial.Serial(device.device, 9600, timeout=1) as con:
                temp_response = con.read(999999).decode("utf-8") # 999999byteまで取得
        except Exception as e:
            temp_response = str(e)
        finally:
            temp = {"name":device.description, "type":"serial", "response":temp_response}
            eel.reload_connection_list({device.device:temp}) # type:ignore
            device_list[device.device] = temp

    # Bluetooth
    for device in bluetooth.discover_devices(lookup_names=True,lookup_class=False): # ここで10秒くらいかかる
        temp_response = "Timeout"
        try:
            with bluetooth.BluetoothSocket(bluetooth.RFCOMM) as con:
                con.connect((device[0], 1))
                temp_response = con.recv(1024).decode("utf-8")
        except Exception as e:
            temp_response = str(e)
        finally:
            temp = {"name":device[1], "type":"bluetooth", "response":temp_response}
            eel.reload_connection_list({device[0]:temp}) # type:ignore
            device_list[device[0]] = temp

    eel.progress_manager("connection_list_update_done") # type:ignore

    return device_list


def generate_dummy_data(dic):
    for k in dic.keys():
        dic[k] += int((random.random() * 10) - 5)
        dic[k] = max(0, dic[k])
    return dic


def receive_send_data():
    global is_continue_receive_send_data, latest_data_dict
    filename = f"store/indicators_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not is_disabled_background_logging:
        with open(filename, mode="a", encoding="UTF-8") as file:
            file.write("datetime," + ",".join(latest_data_dict.keys()) + "\n")
    while is_continue_receive_send_data:
        if is_use_dummy_data:
            latest_data_dict = generate_dummy_data(latest_data_dict)  # 一時的にデータを生成する
        eel.Data_PY2JS(latest_data_dict)  # type: ignore
        if not is_disabled_background_logging:
            with open(filename, mode="a", encoding="UTF-8") as file:
                file.write(str(dt.now()) + ",".join([str(num) for num in latest_data_dict.values()]) + "\n")
        eel.sleep(random.random() / 5)

# ---- データ処理関連ここまで ----

# ---- GUI生成関連 ----
def start_window():
    global is_window_shown
    is_window_shown = True
    eel.start(
        'index.html',
        size=(1280, 720),
        mode='chrome',
        port=0,  # ポートを自動的に設定する
        host='localhost',
        close_callback=after_closed_window,
        block=False
    )
    eel.Get_Initial_Settings(initial_settings) # type: ignore

    update_connection_list_th = Thread(target=get_device_list)
    update_connection_list_th.start()

def after_closed_window(page, socket):
    global is_window_shown
    is_window_shown = False


def kill_entire_system():
    global is_continue_receive_send_data
    while True:
        if thread.is_alive():
            is_continue_receive_send_data = False
        else:
            sys.exit()

# ---- GUI生成関連ここまで ----

# ---- その他関数類 ----
def load_JsonWithComment(path):
    with open(path, mode="r", encoding="UTF-8") as file:
        raw_text = file.read()
    text_comments_removed = re.sub(r'/\*[\s\S]*?\*/|//.*', '', raw_text)
    setting = json.loads(text_comments_removed)
    return setting

# ---- その他関数類ここまで ----

# ---- Args ----
print("Args:", sys.argv)
## --DisableBackGroundLogging : ログファイルの生成を停止する。デバッグ用
is_disabled_background_logging = "--DisableBackGroundLogging" in sys.argv
#
## --UseDummyData : ログファイルの生成を停止する。デバッグ用
is_use_dummy_data = "--UseDummyData" in sys.argv
#
# ---- Argsここまで ----

if __name__ == "__main__":
    # CSVファイルの保存先ディレクトリを生成
    if not os.path.exists("store"):
        os.mkdir("store")

    # あらかじめinterfaceフォルダの親ディレクトリに移動してから実行する（でないとエラーになる）
    # interfaceフォルダにhtmlやcssを入れる
    eel.init("interface")

    # load setting.json
    for k in initial_settings["values"]["data_list"].keys():
        latest_data_dict[k] = 0  # 初期化

    # load settings.env.json
    if os.path.exists(path_antecedence_settings):
        antecedence_setting = load_JsonWithComment(path_antecedence_settings)
        initial_settings["values"].update(antecedence_setting)

    thread = Thread(target=receive_send_data)
    thread.start()
    start_window()

    # ウィンドウ終了時にロギングを継続し、プログラムを終了するか尋ねる
    while True:
        eel.sleep(0.1)  # waitさせないとページにアクセスできない
        if is_disabled_background_logging == True and is_window_shown == False:
            kill_entire_system()
        if is_disabled_background_logging == False and is_window_shown == False:
            input_character = input("ダッシュボードを閉じましたが、システムは稼働しています。\nシステム(Python)を終了する -> c\nもう一度ダッシュボードを開く -> o\n")
            if input_character == "c":
                kill_entire_system()
            elif input_character == "o":
                start_window()
