import yaml

from s3_operations.custom_log import handle_exception

# 例外通知用に処理情報を設定
CONTEXT = f"{__name__}.py >>> 設定読込処理"

# 設定ファイルの指定
CONFIG_FILE = "config.yml"


def load_config() -> dict:
    """
    YAML形式の設定ファイルを読み込み、指定された環境設定を検証して返します。

    Returns:
        dict: 設定ファイルから読み込まれた設定の辞書。

    Raises:
        ValueError: 'environment'キーが存在しない、または'environments'に含まれていない場合に発生します。
    """
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        environment = config.get("environment")
        error_message = (
            f"environment : {environment} : 実行環境の指定が正しくありません。"
            "'environments'の中から環境を選択し 'environment' にセットしてください"
        )

        if not environment:
            raise ValueError(error_message)
        elif environment not in config["environments"]:
            raise ValueError(error_message)
        return config


def report_config(file_name: str, messages: list[str]) -> None:
    """
    設定やステータスメッセージを整形して出力します。

    Args:
        file_name (str): レポートの対象となるファイル名や識別子。
        messages (list[str]): 出力するメッセージのリスト。
    """
    print("\n")
    print("====================================")
    print(f"| {file_name}")
    for msg in messages:
        print(f"| {msg}")
    print("====================================")


# 設定をロード
try:
    CONFIG: dict = load_config()

    # 現在の環境設定を取得
    ENVIRONMENT: str = CONFIG["environment"]
    ENV_CONFIG: dict = CONFIG["environments"][ENVIRONMENT]

    # AWSの設定
    AWS_ACCESS_KEY_ID: str = ENV_CONFIG["aws"]["access_key_id"]
    AWS_SECRET_ACCESS_KEY: str = ENV_CONFIG["aws"]["secret_access_key"]
    AWS_REGION: str = ENV_CONFIG["aws"]["region"]
    S3_BUCKET: str = ENV_CONFIG["aws"]["bucket_name"]

    # CDNオリジンのドメイン設定（例：CloudFrontのドメイン）
    CDN_DOMAIN: str = ENV_CONFIG["cdn_origin"]["domain"]

    # 共通のファイル設定
    DELETE_URL_LIST: str = CONFIG["data"]["params"]["delete_url_list"]
    DELETE_RESULT: str = CONFIG["data"]["logs"]["delete_results"]
    UPLOAD_FILE_LIST: str = CONFIG["data"]["params"]["upload_file_list"]
    RESOURCE: str = CONFIG["data"]["resources"]["files"]
    UPLOAD_RESULT: str = CONFIG["data"]["logs"]["upload_results"]

    # 設定内容の確認出力用
    CONFIG_SUMMARY: list[str] = [
        f"✅ Using `{ENVIRONMENT}` environment",
        f"✅ Bucket Name: {S3_BUCKET}",
    ]

except Exception as e:
    handle_exception(e, CONTEXT)
    raise SystemExit(1)
