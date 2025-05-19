import os
import time
from urllib import request

import boto3

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
)


def create_s3_client():
    """AWS S3 クライアントを生成して返す。

    環境変数や設定ファイルから取得した AWS 認証情報を使用して、
    boto3 の S3 クライアントオブジェクトを作成する。

    Returns:
        boto3.client: 作成された S3 クライアントオブジェクト。
    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    return s3_client


def is_url_accessible(url: str, retries: int = 2, delay: float = 1.5) -> bool:
    """指定した URL にアクセス可能かを確認する。

    Args:
        url (str): アクセス対象の URL。
        retries (int, optional): 試行回数。デフォルトは 2 回。
        delay (float, optional): リトライ間の待機時間（秒）。デフォルトは 1.5 秒。

    Returns:
        bool: アクセスに成功した場合は True、失敗した場合は False。
    """
    for attempt in range(retries):
        try:
            with request.urlopen(url) as response:
                if response.status == 200:
                    return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(delay)
    return False


def write_results_to_file(
    success_list: list[dict], failure_list: list[dict], output_file: str
) -> str:
    """成功・失敗した処理結果をファイルに出力する。

    Args:
        success_list (list[str]): 処理に成功した項目のリスト。
        failure_list (list[dict]): 処理に失敗した項目のリスト。
            各辞書には 'file_name', 'reason', 'path' のキーを含む。
        output_file (str): 出力先ファイルのパス。

    Returns:
        str: 出力したログファイルの絶対パス。
    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("SUCCESS ++++++++++++++++++++++++\n")
        for d in success_list:
            line = "\t".join(str(v) for v in d.values())
            f.write(f"{line}\n")

        f.write("\nFAILURE ------------------------\n")
        for item in failure_list:
            f.write(f"[{item['file_name']}] {item['reason']} : {item['path']}\n")

    return os.path.abspath(output_file)


def load_file(path: str) -> list[str]:
    """指定したファイルを読み込み、空行を除いたリストを返す。

    Args:
        path (str): 入力ファイルのパス。

    Returns:
        list[str]: 空行を除いた各行（文字列）のリスト。
    """
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def notify_output(path: str) -> None:
    """処理結果ファイルのパスをカラー表示で通知する。

    Args:
        path (str): 表示する出力ファイルのパス。
    """
    color = {
        "main": "\033[33m",  # yellow
        "reset": "\033[0m",
    }

    print(f"{color['main']}RESULT: {path}{color['reset']}\n")
