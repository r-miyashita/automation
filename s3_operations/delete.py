import re
from urllib import parse

import set_path
from botocore.exceptions import ClientError
from utils import (
    check_url_accessible,
    create_s3_client,
    log_client_error,
    log_default_error,
    log_file_error,
    setup_logger,
    write_results_to_file,
)

from config import AWS_REGION, BUCKET_NAME, DELETE_URL_LIST

# Linter対策のためにダミー変数へ格納。import段階で用済みなので以降は無視してよい
_ = set_path

# エラーログ用にセットアップ関数呼び出し
setup_logger()


def main():
    # s3 クライアントを作成
    s3_client = create_s3_client()
    if s3_client is None:
        print("認証エラーのため処理を終了します。")
        return  # 認証エラー で終了

    # バケットを指定
    s3_bucket_name = BUCKET_NAME
    # バケット不明 or アクセス拒否 の場合終了させる
    try:
        s3_client.head_bucket(Bucket=s3_bucket_name)
    except ClientError as client_error:
        log_client_error(client_error)
        print("クライアントエラーのため処理を終了します。")
        return  # クライアントエラー で終了

    s3_region = AWS_REGION
    s3_domain = f"{s3_bucket_name}.s3.{s3_region}.amazonaws.com"

    success_list = []
    failure_list = []

    try:
        with open(DELETE_URL_LIST, "r", encoding="utf-8") as url_list:
            for line in url_list:
                # s3用のURLに置換する [http~.net | .com] >> [https:// s3ドメイン]
                s3_url = re.sub(
                    r"^https?://[^/]+(\.net|\.com)",
                    f"https://{s3_domain}",
                    line.strip(),
                )

                # オリジンより後ろの部分を s3キー として切り取る
                s3_key = parse.unquote(s3_url).split(s3_domain + "/")[1]

                # URLが有効であれば、削除処理に入る
                if check_url_accessible(s3_url):
                    try:
                        # オブジェクトの存在確認
                        s3_client.head_object(Bucket=s3_bucket_name, Key=s3_key)

                        # 削除処理
                        s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_key)

                        # オブジェクトの一覧を取得
                        versions = s3_client.list_object_versions(
                            Bucket=s3_bucket_name, Prefix=s3_key
                        )

                        # すべてのバージョンを削除
                        for version in versions.get("Versions", []):
                            version_id = version["VersionId"]
                            s3_client.delete_object(
                                Bucket=s3_bucket_name, Key=s3_key, VersionId=version_id
                            )
                        # 削除マーカーを削除
                        for marker in versions.get("DeleteMarkers", []):
                            marker_id = marker["VersionId"]
                            s3_client.delete_object(
                                Bucket=s3_bucket_name, Key=s3_key, VersionId=marker_id
                            )

                        success_list.append(s3_url)
                    # todo: ログ書き込みにする。client_errorは削除。その他エラーを
                    except Exception as e:
                        reason = str(e)

                        failure_list.append(
                            {"file_name": s3_key, "url": s3_url, "reason": reason}
                        )

                else:
                    failure_list.append(
                        {
                            "file_name": s3_key,
                            "url": s3_url,
                            "reason": "URL not accessible",
                        }
                    )
    except Exception as e:
        if isinstance(e, FileNotFoundError):
            log_file_error(e)
            print(f"{DELETE_URL_LIST}が見つかりません。処理を終了します。")
            return
        else:
            log_default_error(e, "ファイルリスト読込処理")
            print("予期しないエラーが発生しました。処理を終了します。")
            return

    # 処理結果ログ を出力
    write_results_to_file(success_list, failure_list)


if __name__ == "__main__":
    main()
