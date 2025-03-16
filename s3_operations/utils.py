import logging
import time
import traceback
from urllib import request

import boto3
import set_path  # 動作確認用1
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    DELETE_RESULT,
    ERROR_LOG,
)

_ = set_path  # 動作確認用1


# ログ設定 （ デフォルトは error.log ）
def setup_logger(log_file: str = ERROR_LOG):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # ファイルハンドラー設定（ INFO 以上を書き出す ）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [ %(levelname)s ] %(message)s")
    file_handler.setFormatter(formatter)

    # コンソールハンドラー設定（ WARNINF 以上を書き出す ）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # ロガーにハンドラーを追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ログ出力: 認証エラー
def log_auth_error(auth_error):
    logging.error(f"認証エラー: {str(auth_error)}")


# ログ出力: クライアントエラー
def log_client_error(client_error):
    error_code = client_error.response.get("Error", {}).get("Code")
    error_message = str(client_error)
    if error_code == "403":
        logging.error(
            f"クライアントエラー（認証失敗またはアクセス権限不足）： {error_message}"
        )
    elif error_code == "404":
        logging.error(f"クライアントエラー（バケットが不明）： {error_message}")
    else:
        logging.error(f"クライアントエラー（未定義のエラー）： {error_message}")


# ログ出力： ファイルが見つからないエラー
def log_file_error(file_error):
    logging.error(f"指定されたファイルが見つかりません： {str(file_error)}")


# ログ出力： 予期しないエラー
def log_default_error(error, context=""):
    error_type = type(error).__name__
    error_message = str(error)
    error_traceback = traceback.format_exc()
    logging.error(
        f"予期しないエラー： {context} - {error_type}: {error_message}: {error_traceback}"
    )


# s3への接続を行う
def create_s3_client():
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        return s3_client
    except (NoCredentialsError, PartialCredentialsError) as e:
        log_auth_error(e)  # 認証情報が欠けていたらログに書き込み
        return None
    except Exception as e:
        print(f"S3 へ接続中にエラーが発生しました: {e}")
        raise


# URLの疎通確認を行う
def check_url_accessible(url, retries=2, delay=1.5):
    for attempt in range(retries):
        try:
            with request.urlopen(url) as response:
                if response.status == 200:
                    return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(delay)
    return False


# 処理結果ログを出力する
def write_results_to_file(success_list, failure_list, output_file=DELETE_RESULT):
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("成功 ####\n")
            for item in success_list:
                f.write(f"{item}\n")

            f.write("\n")

            f.write("失敗 ####\n")
            for item in failure_list:
                f.write(f"[{item['file_name']}] {item['reason']} : {item['url']}\n")

        print(f"結果を{output_file}に出力しました")
    except Exception as e:
        print(f"結果ファイルの出力に失敗しました。: {e}")
