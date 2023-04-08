import eel # https://pypi.org/project/Eel/

import sys
import random
from math import sin
from time import sleep, time
from datetime import datetime as dt

latest_data_dict = {
    "battery_v": 10,
    "battery_a": 10,
    "battery_temp": 10,
    "body_temp": 10,
    "speed": 10,
    "accelerator": 10,
    "break": 10,
}

condition_send_data = ""

def write_log(filename,message):
    with open(filename, mode="a", encoding="UTF-8") as file:
        file.write(message)


def send_data():
    global latest_data_dict, condition_send_data
    condition_send_data = "running"
    filename =f"store/indicators_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, mode="a", encoding="UTF-8") as file:
        file.write("datetime,"+",".join(latest_data_dict.keys()) + "\n")
    while condition_send_data == "running":
        latest_data_dict = generate_dummy_data(latest_data_dict)  # 一時的にデータを生成する
        eel.Data_PY2JS(latest_data_dict) # type: ignore
        with open(filename, mode="a", encoding="UTF-8") as file:
            file.write(str(dt.now())+",".join([str(num) for num in latest_data_dict.values()]) + "\n")
        eel.sleep(random.random() / 5)
    condition_send_data = "closed"

def generate_dummy_data(dic):
    for k in dic.keys():
        dic[k] += int((random.random() * 10) - 5)
    return dic


def after_closed_window(page, socket):
    global condition_send_data
    # Windowを閉じた後に実行したいコード
    while True:
        input_character = input("ダッシュボードを閉じましたが、システムは稼働しています。\nシステム(Python)を終了する -> c\nもう一度ダッシュボードを開く -> o\n")
        if input_character == "c":
            while condition_send_data == "running":
                # send_dataスレッドが終了するまで待つ
                condition_send_data = "close_wait"
            sys.exit()
        elif input_character == "o":
            start_window()


if __name__ == "__main__":
    # あらかじめinterfaceフォルダの親ディレクトリに移動してから実行する（でないとエラーになる）
    eel.init("interface")  # interfaceフォルダにhtmlやcssを入れる
    eel.spawn(send_data)  # PythonからJSにデータを送信するためのスレッドを立てる
    eel.start(
        'index.html',
        size=(1000, 600),
        mode='chrome',
        port=0, # ポートを自動的に設定する
        host='localhost',
        close_callback=after_closed_window
    )