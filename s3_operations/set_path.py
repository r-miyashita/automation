import os
import sys


# 現在階層を起点にrootを指定し、パスに追加
def configure_path():
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


configure_path()

# パス設定用のモジュール
# 実行スクリプトは　モジュール参照エラー回避目的で これを読み込むようにする

# rootの指定は相対的なので、各階層で専用の set_path を用意する
