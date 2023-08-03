""" Python3標準ライブラリ """
import json
import re
import os
import sys
import time
import math
import random
import warnings
import tracemalloc
from datetime import datetime as dt
from threading import Thread

# https://pypi.org/project/Eel/
# https://qiita.com/inoory/items/f431c581332c8d500a3b
# pip install Eel
import eel  # 起動時にかかる時間の16％が費やされている


# https://pypi.org/project/pyserial/
# pip install pyserial
import serial
from serial.tools import list_ports
from serial.serialutil import SerialException

latest_window_alive_check_epoch: float = time.time()
latest_data_dict: dict = dict()  # 最新のデータのみを格納する
latest_timestamp: str = ""
latest_ID: int = 1
device_dict: dict = dict()
is_window_shown: bool = False
is_continue_receive_send_data: bool = True
main_connection = None
logging_filename: str = ""
BAUD_RATE = 9600

# ---- 設定項目 ----
# INITIAL_SETTINGSは初期設定であり、PATH_PRIMARY_SETTINGSに記述されている設定が優先されます。
# PATH_PRIMARY_SETTINGSにファイルがなければ、初回起動時にINITIAL_SETTINGSの内容がコピーされます。
TIRE_PULSE_PER_CYCLE = 48  # タイヤが一回転するごとに発生するパルス量
TIRE_CIRCUMFERENCE_MM = 1730  # タイヤの円周(ミリメートル)
KELVIN = 273.15  # 0度のときの絶対温度

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
        "body": {
            "initial_battery_ah": "ソーラーカーに搭載されたバッテリーの初期残存量を指定します。単位はAh。",
        },
    },
    "values": {
        "interface": {
            "update_interval_sec": 1,
            "graph_max_display": 100,
            "dark_mode": False,
        },
        "data_logging": {"data_log_dir": "store", "data_log_filename": "log"},
        "body": {"initial_battery_ah": 4000},
        "data_sort": [
            "raw_battery_volts",
            "raw_battery_ampere",
            "raw_solar_volts",
            "raw_solar_ampere",
            "raw_body_speed",
            "raw_battery_temperature_R",
            "raw_battery_temperature_L",
            "raw_ID",
        ],
        "data_list": {
            "raw_battery_volts": {"display_name": "raw_battery_volts", "unit": ""},
            "raw_battery_ampere": {"display_name": "raw_battery_ampere", "unit": ""},
            "raw_solar_volts": {"display_name": "raw_solar_volts", "unit": ""},
            "raw_solar_ampere": {"display_name": "raw_solar_ampere", "unit": ""},
            "raw_body_speed": {"display_name": "raw_body_speed", "unit": ""},
            "raw_battery_temperature_R": {"display_name": "raw_battery_temperature_R", "unit": ""},
            "raw_battery_temperature_L": {"display_name": "raw_battery_temperature_L", "unit": ""},
            "raw_ID": {"display_name": "raw_ID", "unit": ""},
            "body_speed": {"display_name": "機体速度", "unit": "km/h", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 0, "input_sort": 0, "is_show_graph": True},
            "body_traveled_distance": {"display_name": "機体積算移動距離", "unit": "km", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 1, "input_sort": 1},
            "body_temperature": {"display_name": "機体温度", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 2, "input_sort": 2},
            "body_regeneration_rate": {"display_name": "機体回生", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 3, "input_sort": 3},
            "body_accelerator": {"display_name": "機体アクセル", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 4, "input_sort": 4},
            "body_break": {"display_name": "機体ブレーキ", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 5, "input_sort": 5},
            "motor_volts": {"display_name": "モーター電圧", "unit": "V", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 6, "input_sort": 6},
            "motor_ampere": {"display_name": "モーター電流", "unit": "A", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 7, "input_sort": 7},
            "motor_watts": {"display_name": "モーター電力", "unit": "W", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 8, "input_sort": 8},
            "motor_temperature": {"display_name": "モーター温度", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 9, "input_sort": 9},
            "motor_accumulated_power": {"display_name": "モーター積算消費電力", "unit": "Wh", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 10, "input_sort": 10},
            "battery_volts": {"display_name": "バッテリー電圧", "unit": "V", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 11, "input_sort": 11, "is_show_graph": True},
            "battery_ampere": {"display_name": "バッテリー電流", "unit": "A", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 12, "input_sort": 12, "is_show_graph": True},
            "battery_watts": {"display_name": "バッテリー電力", "unit": "W", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 13, "input_sort": 13},
            "battery_temperature_R": {"display_name": "バッテリー温度(右)", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 14, "input_sort": 14, "is_show_graph": True},
            "battery_temperature_L": {"display_name": "バッテリー温度(左)", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 14, "input_sort": 14, "is_show_graph": True},
            "battery_accumulated_power": {"display_name": "バッテリー積算出力電力", "unit": "Wh", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 15, "input_sort": 15},
            "battery_remain_power_percent": {"display_name": "バッテリー残量", "unit": "%", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 16, "input_sort": 16},
            "battery_remain_power_ah": {"display_name": "バッテリー残量", "unit": "Ah", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 17, "input_sort": 17, "is_show_graph": True},
            "battery_weak_volts": {"display_name": "バッテリー弱電電圧", "unit": "V", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 18, "input_sort": 18},
            "solar_volts": {"display_name": "ソーラー電圧", "unit": "V", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 19, "input_sort": 19, "is_show_graph": True},
            "solar_ampere": {"display_name": "ソーラー電流", "unit": "A", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 20, "input_sort": 20, "is_show_graph": True},
            "solar_watts": {"display_name": "ソーラー電力", "unit": "W", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 21, "input_sort": 21},
            "solar_temperature": {"display_name": "ソーラー温度", "unit": "℃", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 22, "input_sort": 22},
            "solar_accumulated_power": {"display_name": "ソーラー積算発電量", "unit": "Wh", "safe_range_min": -10000, "safe_range_max": 10000, "y_lim_min": 0, "y_lim_max": 100, "display_sort": 23, "input_sort": 23},
        },
    },
}
TROUBLE_SHOOTING_GUIDES = {
    # "エラー文": "解説文",
    "OSError(22, 'セマフォがタイムアウトしました。": "このポートは無効である可能性があります。",
    "PermissionError(13, 'アクセスが拒否されました。'": "他のソフトウェアによってポートが使用されている可能性があります。該当するソフトウェアを終了するか、ポートを使用されていない状態にしてください。",
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
    connect_to_id: str = "None"
    connection_type: str = "None"
    received_text: str = ""
    is_enabled_connection: bool = True
    before_parsed_epoch_sec: float = time.time()

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
            self.connection_serial = serial.Serial(self.connect_to_id, BAUD_RATE, timeout=1)
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
        eel.add_remove_notification(False, "CONNECTION_ESTABLISHED", "C", "接続が成功しました。")  # type: ignore

    def connection_observer(self) -> None:
        """
        Observes the connection and receives data from the device. If using dummy data,
        generates random data. If using serial or bluetooth, reads data from the connection.
        Parses the received text and updates the latest data dictionary.

        Returns:
            None
        """
        global latest_timestamp, latest_ID
        SEPARATE_VALUE_VALUE = ","
        SEPARATE_EACH_UPDATE = "#"

        while self.is_enabled_connection:
            eel.sleep(0.05)
            data = ""

            # Get the latest data
            if self.connection_type == "DummyPort":
                # If using dummy data, generate random data
                eel.sleep(random.random() / 5)
                latest_ID += 1
                dummy_data_temp = list()
                for key in INITIAL_SETTINGS["values"]["data_sort"]:
                    # 雑に値を設定する（精度や現実性を重視しない）
                    if "_ampere" in key:
                        dummy_data_temp.append(random.randrange(90000, 100000))
                    elif "_volts" in key:
                        dummy_data_temp.append(random.randrange(250000, 350000))
                    elif "_temperature" in key:
                        dummy_data_temp.append(random.randrange(100, 1000))
                    elif "_speed" in key:
                        dummy_data_temp.append(random.randrange(20, 65))
                    elif "ID" in key:
                        dummy_data_temp.append(latest_ID)
                    else:
                        dummy_data_temp.append(max(0, latest_data_dict[key] + int((random.random() * 10) - 5)))
                data = SEPARATE_VALUE_VALUE.join(map(str, dummy_data_temp)) + SEPARATE_EACH_UPDATE

            elif self.connection_type == "Serial":
                # If using serial, read data from the connection
                data = self.connection_serial.read(999999).decode("utf-8")  # Up to 999999 bytes # Takes about 0.5-1 sec to process?

            # Send the data
            if len(data) > 0:
                self.received_text += data.replace("\r", "").replace("\n", SEPARATE_EACH_UPDATE)
                _print(self.received_text)

            is_do_update_graph = (SEPARATE_VALUE_VALUE in self.received_text and SEPARATE_EACH_UPDATE in self.received_text) or latest_timestamp != ""
            if is_do_update_graph:
                # Parse the received text
                new_data_dict = dict()
                for i, key in enumerate(self.received_text.split(SEPARATE_VALUE_VALUE)):
                    if i < len(INITIAL_SETTINGS["values"]["data_sort"]):
                        new_data_dict[INITIAL_SETTINGS["values"]["data_sort"][i]] = float(re.sub(r"[^0-9.]", "", key))
                _print(new_data_dict)

                is_ID_stepped = True  # int(new_data_dict["ID"]) == int(latest_ID)
                _print(latest_ID, new_data_dict["raw_ID"], is_ID_stepped)
                if len(new_data_dict) > 0 and is_ID_stepped:
                    # Update the latest data dictionary
                    latest_data_dict.update(new_data_dict)

                    # Calculate values (watts, accumulated power, etc.)
                    try:
                        latest_data_dict["battery_volts"] = latest_data_dict["raw_battery_volts"]
                        latest_data_dict["battery_ampere"] = latest_data_dict["raw_battery_ampere"]
                        latest_data_dict["solar_volts"] = latest_data_dict["raw_solar_volts"]
                        latest_data_dict["solar_ampere"] = latest_data_dict["raw_solar_ampere"]
                        latest_data_dict["body_speed"] = latest_data_dict["raw_body_speed"]
                        latest_data_dict["battery_temperature_R"] = latest_data_dict["raw_battery_temperature_R"]
                        latest_data_dict["battery_temperature_L"] = latest_data_dict["raw_battery_temperature_L"]
                        latest_data_dict["ID"] = latest_data_dict["raw_ID"]
                        latest_data_dict["body_speed"] = latest_data_dict["body_speed"] / TIRE_PULSE_PER_CYCLE * TIRE_CIRCUMFERENCE_MM / 1000000 * 3600
                        latest_data_dict["battery_temperature_R"] = 1 / (1 / (25 + KELVIN) + math.log(latest_data_dict["battery_temperature_R"] / (1024 - latest_data_dict["battery_temperature_R"]), 10) / 3435) - KELVIN
                        latest_data_dict["battery_temperature_L"] = 1 / (1 / (25 + KELVIN) + math.log(latest_data_dict["battery_temperature_L"] / (1024 - latest_data_dict["battery_temperature_L"]), 10) / 3435) - KELVIN
                        latest_data_dict["motor_ampere"] *= 3.33 / 1000
                        latest_data_dict["motor_volts"] *= 1.25 * 4 / 1000
                        latest_data_dict["battery_ampere"] *= 3.33 / 1000
                        latest_data_dict["battery_volts"] *= 1.25 * 4 / 1000
                        latest_data_dict["solar_ampere"] *= 3.33 / 1000
                        latest_data_dict["solar_volts"] *= 1.25 * 4 / 1000
                        latest_data_dict["motor_watts"] = latest_data_dict["motor_ampere"] * latest_data_dict["motor_volts"]
                        latest_data_dict["solar_watts"] = latest_data_dict["solar_ampere"] * latest_data_dict["solar_volts"]
                        latest_data_dict["battery_watts"] = latest_data_dict["battery_ampere"] * latest_data_dict["battery_volts"]
                        latest_data_dict["body_traveled_distance"] += latest_data_dict["body_speed"] * (time.time() - self.before_parsed_epoch_sec) / 3600
                        latest_data_dict["motor_accumulated_power"] += latest_data_dict["motor_ampere"] * (time.time() - self.before_parsed_epoch_sec) / 3600
                        latest_data_dict["solar_accumulated_power"] += latest_data_dict["solar_ampere"] * (time.time() - self.before_parsed_epoch_sec) / 3600
                        latest_data_dict["battery_accumulated_power"] += latest_data_dict["battery_ampere"] * (time.time() - self.before_parsed_epoch_sec) / 3600
                        latest_data_dict["battery_remain_power_ah"] = INITIAL_SETTINGS["values"]["body"]["initial_battery_ah"] - latest_data_dict["battery_accumulated_power"]
                        latest_data_dict["battery_remain_power_percent"] = latest_data_dict["battery_remain_power_ah"] / INITIAL_SETTINGS["values"]["body"]["initial_battery_ah"] * 100
                    except (ZeroDivisionError, TypeError, ValueError, KeyError, AttributeError, SyntaxError) as e:
                        _print(e)

                    _print(new_data_dict)
                    eel.Data_PY2JS(latest_data_dict)  # type: ignore
                    _print(latest_data_dict)

                    if not IS_DISABLED_BACKGROUND_LOGGING:
                        # Log the latest data
                        # 一時的にログファイルを生成する処理を行わせる
                        # あとで修正する
                        if logging_filename == "":
                            create_new_logging_file()

                        with open(logging_filename, mode="a", encoding="UTF-8") as file:
                            new_line = str(dt.now()) + "," + ",".join([str(latest_data_dict[key]) for key in sorted(latest_data_dict.keys())]) + "," + latest_timestamp + "\n"
                            file.write(new_line)
                            latest_timestamp = ""
                if "ID" in new_data_dict:
                    latest_ID = new_data_dict["ID"]
                self.before_parsed_epoch_sec = time.time()
                self.received_text = ""


@eel.expose
def receive_timestamp(comment):
    global latest_timestamp
    print(comment)
    latest_timestamp += comment


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
    eel.display_logging_status({"csv_file_path": logging_filename})  # type:ignore
    with open(logging_filename, mode="a", encoding="UTF-8") as file:
        file.write("datetime," + ",".join(sorted(latest_data_dict.keys())) + "\n")


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
    for device in reversed(list_ports.comports()):  # ポート番号の大きいものが接続対象であることが多いため、リストを逆にする
        temp_response = "Timeout"
        try:
            with serial.Serial(device.device, BAUD_RATE, timeout=1) as con:
                temp_response = con.read(999999).decode("utf-8")  # 999999byteまで取得
        except (serial.SerialException, SerialException, KeyError, AttributeError) as error:
            temp_response = str(error)
            _print(error)

            # トラブルシューティングガイドを付与
            for key in TROUBLE_SHOOTING_GUIDES.items():
                if key[0] in temp_response:
                    temp_response += "<br><br>## トラブルシューティング<br>" + key[1]

        finally:
            temp = {device.device: {"name": device.description, "type": "Serial", "response": temp_response, "connected": device.device == now_connection_id}}
            eel.reload_connection_list(temp)  # type:ignore
            device_dict = device_dict | temp

    eel.progress_manager("connection_list_update_done")  # type:ignore


# ---- データ処理関連ここまで ----


# ---- GUI生成関連 ----
@eel.expose
def window_initialize():
    # Windowの起動が完了した段階でJS側から呼び出す
    # Python側の設定(INITIAL_SETTINGS)をJSに送信する
    thread_update_connection_list = Thread(target=get_device_list)
    thread_update_connection_list.start()
    eel.add_remove_notification(IS_DISABLED_BACKGROUND_LOGGING, "IS_DISABLED_BACKGROUND_LOGGING", "L", "[デバッグ機能]ログファイルの生成が停止されています。")  # type: ignore
    eel.add_remove_notification(IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED, "IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED", "C", "[デバッグ機能]ウィンドウ終了時に、バックエンドシステムが終了されます。")  # type: ignore
    eel.add_remove_notification(IS_USE_DUMMY_DATA, "IS_USE_DUMMY_DATA", "D", "[デバッグ機能]ダミーデバイスが有効です。")  # type: ignore
    eel.add_remove_notification(DEBUG_PRINT_MODE, "DEBUG_PRINT_MODE", "P", "[デバッグ機能]デバッグ情報がコンソールに出力されます。")  # type: ignore
    _ = eel.Get_Initial_Settings(INITIAL_SETTINGS)()  # type:ignore


def start_window():
    global is_window_shown
    is_window_shown = True
    eel.start("index.html", size=(1280, 720), mode="chrome", port=0, host="localhost", close_callback=after_closed_window, block=False)  # ポートを自動的に設定する


def after_closed_window(*args):  # type: ignore # pylint: disable=W0613
    # TODO : PCのスリープ時にこの関数が呼び出される不具合を修正する
    global is_window_shown, latest_window_alive_check_epoch
    _print("window_closed")
    # もしWindowが残っている（閉じられたのではなくリロードされた）場合
    # 1秒間の間にwindow_alive_check_fromJSが実行されるため、ウィンドウ終了とリロードを区別することができる
    latest_window_alive_check_epoch = time.time()
    temp = latest_window_alive_check_epoch
    eel.sleep(1)
    is_window_shown = temp != latest_window_alive_check_epoch
    _print("is_window_shown:", is_window_shown)


def kill_entire_system():
    print("すべてのシステムを終了します。")
    for countdown in range(5):
        print(5 - countdown)
        eel.sleep(1)
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
                start_window()


def window_alive_check_fromPy():
    # Pythonから生存確認を実行する（生存確認が行われた時間の記録はJavaScript側）
    while True:
        eel.sleep(0.01)  # waitさせないとページにアクセスできない
        eel.window_alive_check_fromPy()  # type: ignore


@eel.expose
def window_alive_check_fromJS():
    # JavaScriptから生存確認を実行する（生存確認が行われた時間の記録はPython側）
    global latest_window_alive_check_epoch
    latest_window_alive_check_epoch = time.time()


@eel.expose
def apply_new_settings_to_python(dictionary: dict):
    INITIAL_SETTINGS["values"].update(dictionary)
    write_Json(PATH_PRIMARY_SETTINGS, dictionary)


# ---- GUI生成関連ここまで ----


# ---- その他関数類 ----
def load_JsonWithComment(path):
    try:
        with open(path, mode="r", encoding="UTF-8") as file:
            raw_text = file.read()
        text_comments_removed = re.sub(r"/\*[\s\S]*?\*/|//.*", "", raw_text)
        setting = json.loads(text_comments_removed)
        return setting
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return dict()


def write_Json(_path: str, _dict: dict) -> None:
    with open(_path, mode="w", encoding="UTF-8") as file:
        json.dump(_dict, file)


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
#
# --ClosePythonWhenWindowClosed : ウィンドウを閉じる時にPythonを終了する
IS_CLOSE_PYTHON_WHEN_WINDOW_CLOSED = "--ClosePythonWhenWindowClosed" in sys.argv
#
# --UseDummyData : ダミーのデバイスを利用できる。デバッグ用
IS_USE_DUMMY_DATA = "--UseDummyData" in sys.argv
#
# --DebugPrint : デバッグモード有効時にのみPrintする。デバッグ用
DEBUG_PRINT_MODE = "--DebugPrint" in sys.argv

if not DEBUG_PRINT_MODE:
    # エラーや警告を非表示
    warnings.simplefilter("ignore")
else:
    # エラーや警告をすべて表示
    tracemalloc.start()
    warnings.resetwarnings()
#
os.system("cls")  # コンソールクリア
_print("Args:", sys.argv)
# ---- Argsここまで ----

if __name__ == "__main__":
    # CSVファイルの保存先ディレクトリを生成
    if not os.path.exists(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"]):
        try:
            os.mkdir(INITIAL_SETTINGS["values"]["data_logging"]["data_log_dir"])
        except PermissionError:
            print("ログファイルの保存先ディレクトリを作成できません。\nアプリ修了後に、アプリ(EXEファイル)をZipファイルから解凍して、実行してください。")

    # load setting.json
    for k in INITIAL_SETTINGS["values"]["data_list"]:
        latest_data_dict[k] = 0  # 初期化

    # load settings.env.json
    if os.path.exists(PATH_PRIMARY_SETTINGS):
        antecedence_setting = load_JsonWithComment(PATH_PRIMARY_SETTINGS)
        INITIAL_SETTINGS["values"].update(antecedence_setting)

    thread_window_alive_check_fromPy = Thread(target=window_alive_check_fromPy, daemon=True)
    thread_window_alive_check_fromPy.start()

    start_window()
    continue_logging_and_exit()
