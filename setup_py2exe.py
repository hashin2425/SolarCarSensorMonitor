from distutils.core import setup
import py2exe
from glob import glob

py2exe_options = {
    "compressed": 1,
    "optimize": 2,
    "bundle_files": 2,

    # 必要な／不必要なモジュールを指定
    "includes":[],
    "excludes":[],
}

include_data = [
    # ('フォルダ名', ['コピーファイル 相対パス'])
    ("interface", glob("./interface/**/*.*", recursive=True)),
]

py2exe.freeze(
    options = {"py2exe": py2exe_options},
    console = [
        {
        "script" : "mainrun.py",
        }
    ],
    data_files = include_data,
    zipfile = "result.zip"
)