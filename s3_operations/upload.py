import mimetypes
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
    CDN_DOMAIN,
    CONFIG_SUMMARY,
    ENVIRONMENT,
    RESOURCE,
    S3_BUCKET,
    UPLOAD_FILE_LIST,
    UPLOAD_RESULT,
    report_config,
)

CONTEXT = {
    "create_s3client": "s3クライアント生成",
    "connect_bucket": "バケット疎通確認",
    "load_file_list": "ファイルリスト読込",
    "setup_upload_resource": "リソース準備",
    "upload_s3_object": "s3オブジェクトアップロード",
    "set_access_url": "アクセスURL生成",
    "write_results": "結果リスト生成",
}

# エンコード除外キーワード をセット
EXCLUDE_CHARS = "/-_.~!*'()+"


def setup_upload_resources(s3_key_list: list) -> tuple[list[dict], list[dict]]:
    """
    アップロード対象のファイル情報と、存在しないファイルの情報を準備する。

    Args:
        s3_key_list (list): アップロード対象のS3キーのリスト。

    Returns:
        tuple[list[dict], list[dict]]:
            - upload_items: 存在するファイルの情報リスト（file_name, key, extra_args）。
            - not_found_files: 存在しないファイルの情報リスト（file_name, reason, path）。

    Raises:
        PermissionError: リソースディレクトリまたはファイルへのアクセス権がない場合。
    """
    # リソース用のディレクトリ指定
    resource_dir = Path(RESOURCE)

    upload_items = []
    not_found_files = []

    for key in s3_key_list:
        resource_file = resource_dir / Path(key).name

        if not resource_file.exists():
            not_found_files.append(
                {
                    "file_name": str(resource_file.name),
                    "reason": "アップロード対象のファイルが見つかりません",
                    "path": str(resource_file),
                }
            )
            continue

        # リソースが存在したらアップロード情報をセットする
        upload_items.append(
            {
                "resource_file": str(resource_file),
                "key": key,
                "extra_args": set_extra_args(resource_file),
            }
        )

    return upload_items, not_found_files


def set_extra_args(file: Path) -> dict:
    """
    推測されるMIMEタイプに基づいて、S3アップロード時の追加パラメータを設定する。

    Args:
        file (Path): アップロード対象のファイルパス。

    Returns:
        dict: 以下のキーを持つ辞書。
            - "ACL": アクセス権（常に "public-read"）
            - "ContentType": 推測されたまたはデフォルトの MIME タイプ
    """
    # MIMEタイプを取得 #mime_type の例: 'image/jpeg'
    mime_type, _ = mimetypes.guess_type(file)

    return {
        "ACL": "public-read",
        # MIMEタイプ不明な場合は 'application/octet-stream'とする
        "ContentType": mime_type if mime_type else "application/octet-stream",
    }


def upload_s3_object(
    s3_client: BaseClient, upload_items: list[dict]
) -> tuple[list[dict], list[dict]]:
    """
    指定されたファイルをS3にアップロードし、成功・失敗結果を返す。

    Args:
        s3_client (BaseClient): boto3のS3クライアント。
        upload_items (list[dict]): アップロード対象の情報リスト。
            各辞書には以下を含む:
                - 'resource_file': ローカルファイルパス
                - 'key': S3キー
                - 'extra_args': S3アップロード時の追加引数（ACL, ContentTypeなど）

    Returns:
        tuple[list[dict], list[dict]]:
            - succeed_items: アップロード成功ファイルの情報（file_name, key）
            - failure_list: アップロード失敗ファイルの情報（file_name, reason, path）

    Notes:
        例外はキャッチされ、failure_list に記録される。
    """
    succeed_items = []
    failure_list = []
    for item in upload_items:
        try:
            s3_client.upload_file(
                Filename=item["resource_file"],
                Bucket=S3_BUCKET,
                Key=item["key"],
                ExtraArgs=item["extra_args"],
            )

            succeed_items.append(
                {"file_name": str(Path(item["key"]).name), "key": item["key"]}
            )

        except Exception as e:
            reason = str(e)
            failure_list.append(
                {
                    "file_name": str(Path(item["key"]).name),
                    "reason": f"S3アップロード失敗: {reason}",
                    "path": "-",
                }
            )

    return succeed_items, failure_list


def create_access_url(s3_key: str) -> str:
    """
    S3キーから環境に応じた公開アクセスURLを生成する。

    Args:
        s3_key (str): アップロード対象ファイルのS3キー。

    Returns:
        str: 公開アクセス用URL（CloudFront または S3 オリジナルドメイン）。
    """

    # s3キーを パーセンドエンコードする
    encoded_key = parse.quote(s3_key, safe=EXCLUDE_CHARS)

    # 返却用のURLをセット
    url_replaced_domain = f"https://{CDN_DOMAIN}/{encoded_key}"
    url_original_domain = (
        f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{encoded_key}"
    )

    # env設定の環境が本番であれば、CDN用のドメインに置換したURLを返す
    return url_replaced_domain if ENVIRONMENT == "production" else url_original_domain


def set_access_url(s3_objects: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    アップロード済みオブジェクトのアクセスURLを生成し、検証結果を返す。

    Args:
        s3_objects (list[dict]): アップロード成功ファイルの情報リスト（file_name, key）。

    Returns:
        tuple[list[dict], list[dict]]:
            - success_list: 有効なURLのファイル情報（file_name, path）
            - failure_list: 無効なURLのファイル情報（file_name, path, reason）
    """
    success_list = []
    failure_list = []

    for obj in s3_objects:
        access_url = create_access_url(obj["key"])

        new_obj = {"file_name": obj["file_name"], "path": access_url}

        # URLが無効であれば失敗リストにセット
        if not is_url_accessible(new_obj["path"]):
            new_obj["reason"] = "URLが無効です"
            failure_list.append(new_obj)
            continue

        # URLが有効であれば成功リストにセット
        success_list.append(new_obj)

    return success_list, failure_list


# メイン処理
def main():
    # 開始通知
    report_config(Path(__file__).name, CONFIG_SUMMARY)
    start()

    # s3 クライアントを作成
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

    # アップロードリスト読込
    context = CONTEXT["load_file_list"]
    try:
        s3_key_list = load_file(UPLOAD_FILE_LIST)
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # アップロード用のリソース情報生成
    context = CONTEXT["setup_upload_resource"]
    try:
        upload_items, setup_upload_resource_failure_list = setup_upload_resources(
            s3_key_list
        )
        notify(context)
    except Exception as e:
        handle_exception(e, context)
        end()
        return

    # アップロード処理
    context = CONTEXT["upload_s3_object"]
    succeed_items, upload_s3_object_failure_list = upload_s3_object(
        s3_client, upload_items
    )
    notify(context)

    # アクセスURLの生成
    context = CONTEXT["set_access_url"]
    success_list, set_access_url_failure_list = set_access_url(succeed_items)
    notify(context)

    # 失敗リストのマージ
    # 各処理で排出された 失敗リストをマージ
    failure_list = [
        *setup_upload_resource_failure_list,
        *upload_s3_object_failure_list,
        *set_access_url_failure_list,
    ]

    # 結果書き込み
    context = CONTEXT["write_results"]
    try:
        path = write_results_to_file(success_list, failure_list, UPLOAD_RESULT)
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

# スクリプト実行
if __name__ == "__main__":
    main()
