import re
from pathlib import Path
from urllib import parse

from botocore.client import BaseClient
from custom_log import end, handle_exception, notify, setup_logger, start
from utils import (
    create_s3_client,
    is_url_accessible,
    load_file,
    notify_output,
    write_results_to_file,
)

from config import (
    AWS_REGION,
    CONFIG_SUMMARY,
    DELETE_RESULT,
    DELETE_URL_LIST,
    S3_BUCKET,
    report_config,
)

CONTEXT = {
    "create_s3client": "s3クライアント生成",
    "connect_bucket": "バケット疎通確認",
    "load_url_list": "URLリスト読込",
    "delete_s3_object": "s3オブジェクト削除",
    "write_results": "結果リスト生成",
}

REGX = r"^https?://[^/]+(\.net|\.com)"


def create_s3_key_and_s3_url(
    original_url: str, s3_origin: str, delimiter: str
) -> tuple[str, str]:
    """
    元のパブリックURLを指定された S3 オリジンに置き換えた新しい S3 URL と、
    その URL から取得した S3 オブジェクトキーを生成します。

    Parameters:
        original_url (str): 元のファイルURL（例: https://example.com/...）。
        s3_origin (str): 置換後の S3 のパブリックURL の起点（例: https://bucket-name.s3.amazonaws.com）。
        delimiter (str): S3 キーの抽出に使用する区切り文字列。

    Returns:
        tuple[str, str]:
            - s3_key (str): 生成された S3 オブジェクトキー。
            - s3_url (str): S3 オリジンに置き換えた URL。
    """
    # 元のURLをs3パブリックURLへ置換する
    s3_url = re.sub(REGX, s3_origin, original_url)

    # パブリックURLからs3キーを生成する
    s3_key = parse.unquote(s3_url).split(delimiter)[1]

    return s3_key, s3_url


def delete_object_versions(s3_client: BaseClient, s3_key: str) -> None:
    """
    指定された S3 オブジェクトのすべてのバージョンと削除マーカーを削除します。

    この関数は、指定されたバケットとキーに対応するオブジェクトが存在するか確認した後、
    バージョン管理が有効なバケットから該当オブジェクトの全バージョンと削除マーカーを削除します。

    Parameters:
        s3_client (BaseClient): Boto3 の S3 クライアントインスタンス。
        s3_key (str): 削除対象のオブジェクトキー（ファイルパス）。

    Raises:
        botocore.exceptions.ClientError: オブジェクトが存在しない、またはアクセスできない場合など。
        Exception: その他の予期しないエラーが発生した場合。

    Returns:
        None
    """

    # リソースの確認
    s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)

    # オブジェクトのバージョン情報を取得
    versions = s3_client.list_object_versions(Bucket=S3_BUCKET, Prefix=s3_key)

    # ループ処理で バージョン と 削除マーカー をそれぞれ削除する
    for attr in ["Versions", "DeleteMarkers"]:
        for version in versions.get(attr, []):
            s3_client.delete_object(
                Bucket=S3_BUCKET, Key=s3_key, VersionId=version["VersionId"]
            )

    return


def process_deletions(
    urls: list, s3_origin: str, delimiter: str, s3_client: BaseClient
) -> tuple[list, list]:
    """
    指定されたURLリストに基づき、S3オブジェクトの削除を試み、
    削除に成功したURLと失敗したURLのリストを返す。

    Args:
        urls (list): 削除対象のファイルURLリスト。
        s3_origin (str): S3オリジンのベースURL。S3キーを生成するために使用。
        delimiter (str): S3キー生成時に使用する区切り文字。
        s3_client (BaseClient): boto3のS3クライアントインスタンス。

    Returns:
        tuple[list, list]:
            - success_list: 削除に成功したファイルのS3公開URLのリスト。
            - failure_list: 削除に失敗したファイルの情報（ファイル名、URL、理由）を含む辞書のリスト。
    """
    # 結果リストの用意
    success_list = []
    failure_list = []

    for original_url in urls:
        # URLからオブジェクトのアクセス情報を生成
        s3_key, s3_url = create_s3_key_and_s3_url(original_url, s3_origin, delimiter)

        # URL有効チェック後に削除を行う
        if is_url_accessible(s3_url):
            try:
                delete_object_versions(s3_client, s3_key)
                success_list.append({"url": s3_url})

            except Exception as e:
                # 削除失敗の場合もループは継続
                reason = str(e)
                failure_list.append(
                    {"file_name": s3_key, "path": s3_url, "reason": reason}
                )
        else:
            failure_list.append(
                {"file_name": s3_key, "path": s3_url, "reason": "URL not accessible"}
            )

    return success_list, failure_list


def main():
    # 開始通知
    report_config(Path(__file__).name, CONFIG_SUMMARY)
    start()

    # s3クライアント作成
    context = CONTEXT["create_s3client"]
    try:
        s3_client = create_s3_client()
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # バケットへの疎通確認
    context = CONTEXT["connect_bucket"]
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # 入力ファイルからURLを取り出してリストを生成
    context = CONTEXT["load_url_list"]
    try:
        urls = load_file(DELETE_URL_LIST)
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # 削除処理を行い、結果リストを生成
    context = CONTEXT["delete_s3_object"]

    s3_host = f"{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com"
    s3_origin = f"https://{s3_host}"
    delimiter = f"{s3_host}/"

    success_list, failure_list = process_deletions(
        urls, s3_origin, delimiter, s3_client
    )
    notify(context)

    # 処理結果ログ を出力
    context = CONTEXT["write_results"]
    try:
        path = write_results_to_file(success_list, failure_list, DELETE_RESULT)
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # 終了通知
    end()
    notify_output(path)


# エラーログ用にセットアップ関数呼び出し
setup_logger()

if __name__ == "__main__":
    main()
