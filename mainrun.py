import eel
# https://pypi.org/project/Eel/
# https://qiita.com/inoory/items/f431c581332c8d500a3b
# pip install Eel

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
path_settings = "./settings/settings.json"
path_antecedence_settings = "./settings/settings.env.json"


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
    eel.Get_Initial_Settings(settings) # type: ignore


def load_JsonWithComment(path):
    with open(path, mode="r", encoding="UTF-8") as file:
        raw_text = file.read()
    text_comments_removed = re.sub(r'/\*[\s\S]*?\*/|//.*', '', raw_text)
    setting = json.loads(text_comments_removed)
    return setting



if __name__ == "__main__":
    # CSVファイルの保存先ディレクトリを生成
    if not os.path.exists("store"):
        os.mkdir("store")

    # あらかじめinterfaceフォルダの親ディレクトリに移動してから実行する（でないとエラーになる）
    # interfaceフォルダにhtmlやcssを入れる
    eel.init("interface")

    # load setting.json
    settings = load_JsonWithComment(path_settings)
    for k in settings["data_list"].keys():
        latest_data_dict[k] = 0  # 初期化

    # load settings.env.json
    if os.path.exists(path_antecedence_settings):
        antecedence_setting = load_JsonWithComment(path_antecedence_settings)
        settings.update(antecedence_setting)

    thread = Thread(target=receive_send_data)
    thread.start()
    start_window()

    # ウィンドウ終了時にロギングを継続し、プログラムを終了するか尋ねる
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
