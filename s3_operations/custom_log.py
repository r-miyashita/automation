import logging
import traceback

from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

LOG_FORMAT = {
    "message": "%(asctime)s [ %(levelname)s ] %(message)s",
    "suffix": {"success": "SUCCESS🌟", "failure": "🔥🔥🔥", "start": "🚀", "end": "🌏"},
    "color": {
        "reset": "\033[0m",
        "blue": "\033[94m",
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[33m",
    },
}


class ColorFormatter(logging.Formatter):
    """
    ログレベルに応じて色を変えるカスタムフォーマッター。

    logging.xxx(message) が実行されると、内部的にハンドラーからこのフォーマッターの format() が呼び出され、
    元のログメッセージにレベルに応じた色が付加されて出力される。
    """

    COLOR_MAP = {
        logging.DEBUG: LOG_FORMAT["color"]["blue"],
        logging.INFO: LOG_FORMAT["color"]["green"],
        logging.WARNING: LOG_FORMAT["color"]["yellow"],
        logging.ERROR: LOG_FORMAT["color"]["red"],
        logging.CRITICAL: LOG_FORMAT["color"]["red"],
    }

    def format(self, record):
        # メッセージの中に suffix の start や end が含まれていれば色を強制的に青にする
        msg = str(record.getMessage())
        if LOG_FORMAT["suffix"]["start"] in msg or LOG_FORMAT["suffix"]["end"] in msg:
            color = LOG_FORMAT["color"]["blue"]
        else:
            color = self.COLOR_MAP.get(record.levelno, "")
        reset = LOG_FORMAT["color"]["reset"]
        original_msg = super().format(record)
        return f"{color}{original_msg}{reset}"


def setup_logger():
    """
    ルートロガーに対してコンソール出力用のハンドラーを設定する。

    - ログレベルは DEBUG に設定される（すべてのログが対象）。
    - コンソール出力は INFO レベル以上のログを表示。
    - すでにハンドラーが設定されている場合は再設定を行わず、処理をスキップする。

    この関数は冪等に設計されており、複数回呼び出してもハンドラーの重複追加は起こらない。
    """
    logger = logging.getLogger()

    # ハンドラーがセットアップ済みであれば、処理をスキップする
    if logger.hasHandlers():
        return

    logger.setLevel(logging.DEBUG)
    formatter = ColorFormatter(LOG_FORMAT["message"])

    # コンソールハンドラー設定（ INFO 以上を書き出す ）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ロガーにハンドラーを追加
    logger.addHandler(console_handler)


def handle_exception(e: Exception, context: str = "処理"):
    """
    汎用例外処理ロガー。例外の種類を判定し、統一フォーマットでログ出力する。

    Args:
        e (Exception): 捕捉した例外
        context (str): 処理内容（例: 'S3削除'、'アップロード'）
    """
    suffix = LOG_FORMAT["suffix"]["failure"]

    # s3クライアント生成時のエラー
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        message = f"[{context}] [認証エラー] 認証情報が正しくありません: {e}"

        logging.error(f"{message} {suffix}")

    # バケットやオブジェクトアクセス時のエラー
    elif isinstance(e, ClientError):
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        formatted_message = f"[{context}] [{error_code}] {error_message}"

        logging.error(f"{formatted_message} {suffix}")

    # ファイルが見つからない場合のエラー
    elif isinstance(e, FileNotFoundError):
        message = f"[{context}] [ファイル参照エラー] 指定されたファイルが見つかりません: {e.filename}"

        logging.error(f"{message} {suffix}")

    elif isinstance(e, ValueError):
        error_message = str(e)
        message = f"[{context}] [値エラー] {error_message}"

        logging.error(f"{message} {suffix}")

    # 未定義エラー。詳細まで出力する
    else:
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        formatted_message = f"[{context}] [{error_type}] {error_message}"
        reset_color = LOG_FORMAT["color"]["reset"]

        logging.error(f"{formatted_message} {suffix}\n{reset_color}{error_traceback}")


def notify(context: str):
    suffix = LOG_FORMAT["suffix"]["success"]
    logging.info(f"[{context}] {suffix}")


def start():
    suffix = LOG_FORMAT["suffix"]["start"]
    context = "-------------------------------"
    message = "START"
    logging.info(f"[{context}] {message}{suffix}")


def end():
    suffix = LOG_FORMAT["suffix"]["end"]
    context = "-------------------------------"
    message = "END"
    logging.info(f"[{context}] {message}{suffix}\n")
