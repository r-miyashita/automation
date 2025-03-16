import mimetypes
import os
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

from config import BUCKET_NAME, CLOUD_FRONT_DOMAIN, RESOURCE, UPLOAD_FILE_LIST

_ = set_path

# エラーログ用にセットアップ関数呼び出し
setup_logger()


# エンコード除外キーワード
EXCLUDE_CHARS = "/-_.~!*'()+"


# メイン処理
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

    # リソースフォルダ の指定
    files_dir = RESOURCE

    success_list = []
    failure_list = []

    try:
        # ファイルリスト読み込み
        with open(UPLOAD_FILE_LIST, "r", encoding="utf-8") as file_list:
            # 1行ずつ ファイルパスを取得
            for line in file_list:
                s3_key = line.strip()
                if not s3_key:
                    continue

                # ファイル名を抽出してローカルパスを生成
                file_name = os.path.basename(s3_key)
                upload_file = os.path.join(files_dir, file_name)
                if not os.path.isfile(upload_file):
                    failure_list.append(
                        {
                            "file_name": file_name,
                            "reason": "アップロード対象のファイルが見つかりません",
                        }
                    )
                    continue

                # MIMEタイプを取得 #mime_type の例: 'image/jpeg'
                mime_type, _ = mimetypes.guess_type(upload_file)

                # ExtraArgsを作成
                extra_args = {
                    "ACL": "public-read",
                    # MIMEタイプ不明な場合は 'application/octet-stream'とする
                    "ContentType": mime_type
                    if mime_type
                    else "application/octet-stream",
                }

                try:
                    # ファイルをS3にアップロード
                    s3_client.upload_file(
                        Filename=upload_file,
                        Bucket=s3_bucket_name,
                        Key=s3_key,
                        ExtraArgs=extra_args,
                    )

                    # アップロードしたファイルのパブリックURLを生成
                    encoded_key = parse.quote(s3_key, safe=EXCLUDE_CHARS)
                    public_url = (
                        f"https://{CLOUD_FRONT_DOMAIN}/{encoded_key}"  # 本番用
                        # f'https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{encoded_key}' # 検証用
                        # f'{encoded_key}' # 検証用
                    )

                    # 結果をファイルに書き込み
                    if check_url_accessible(public_url):
                        success_list.append({"file_name": file_name, "url": public_url})
                    else:
                        failure_list.append(
                            {
                                "file_name": file_name,
                                "reason": "URL疎通確認失敗",
                                "url": public_url,
                            }
                        )
                except Exception as e:
                    reason = str(e)

                    failure_list.append(
                        {
                            "file_name": file_name,
                            "reason": f"S3アップロード失敗: {reason}",
                            "url": public_url,
                        }
                    )
        # ファイル出力
        write_results_to_file(success_list, failure_list)

    except Exception as e:
        if isinstance(e, FileNotFoundError):
            log_file_error(e)
            print(f"{UPLOAD_FILE_LIST}が見つかりません。処理を終了します。")
            return
        else:
            log_default_error(e, "ファイルリスト読込処理")
            print("予期しないエラーが発生しました。処理を終了します。")
            return


# スクリプト実行
if __name__ == "__main__":
    main()
