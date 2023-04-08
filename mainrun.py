import eel  # https://pypi.org/project/Eel/

import sys
import random
from math import sin
from time import sleep, time
from datetime import datetime as dt
from threading import Thread

latest_data_dict = {
    "battery_v": 10,
    "battery_a": 10,
    "battery_temp": 10,
    "body_temp": 10,
    "speed": 10,
    "accelerator": 10,
    "break": 10,
}

is_window_shown = False
is_continue_receive_send_data = True


def generate_dummy_data(dic):
    for k in dic.keys():
        dic[k] += int((random.random() * 10) - 5)
    return dic


def receive_send_data():
    global is_continue_receive_send_data, latest_data_dict
    filename = f"store/indicators_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, mode="a", encoding="UTF-8") as file:
        file.write("datetime," + ",".join(latest_data_dict.keys()) + "\n")
    while is_continue_receive_send_data:
        latest_data_dict = generate_dummy_data(latest_data_dict)  # 一時的にデータを生成する
        eel.Data_PY2JS(latest_data_dict)  # type: ignore
        with open(filename, mode="a", encoding="UTF-8") as file:
            file.write(str(dt.now()) + ",".join([str(num) for num in latest_data_dict.values()]) + "\n")
        eel.sleep(random.random() / 5)


def after_closed_window(page, socket):
    global is_window_shown
    is_window_shown = False


def start_window():
    global is_window_shown
    is_window_shown = True
    eel.start(
        'index.html',
        size=(1000, 600),
        mode='chrome',
        port=0,  # ポートを自動的に設定する
        host='localhost',
        close_callback=after_closed_window,
        block=False
    )


if __name__ == "__main__":
    # あらかじめinterfaceフォルダの親ディレクトリに移動してから実行する（でないとエラーになる）
    # interfaceフォルダにhtmlやcssを入れる
    eel.init("interface")
    thread = Thread(target=receive_send_data)
    thread.start()
    start_window()
    while True:
        eel.sleep(0.1)  # waitさせないとページにアクセスできない
        if is_window_shown == False:
            input_character = input("ダッシュボードを閉じましたが、システムは稼働しています。\nシステム(Python)を終了する -> c\nもう一度ダッシュボードを開く -> o\n")
            if input_character == "c":
                while True:
                    if thread.is_alive():
                        is_continue_receive_send_data = False
                    else:
                        sys.exit()
            elif input_character == "o":
                start_window()
