import yaml

# 設定ファイルを読み込む
CONFIG_FILE = "config.yml"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        environment = config.get("environment")
        error_message = f"environment: {environment}: 設定が正しくありません。'environments'の中から環境を選択し 'environment' にセットしてください: {CONFIG_FILE}"

        if not environment:
            raise ValueError(error_message)
        elif environment not in config["environments"]:
            raise ValueError(error_message)
        return config


# 設定をロード
CONFIG = load_config()

# 現在の環境設定を取得
ENVIRONMENT = CONFIG["environment"]

ENV_CONFIG = CONFIG["environments"][ENVIRONMENT]

# AWSの設定
AWS_ACCESS_KEY_ID = ENV_CONFIG["aws"]["access_key_id"]
AWS_SECRET_ACCESS_KEY = ENV_CONFIG["aws"]["secret_access_key"]
AWS_REGION = ENV_CONFIG["aws"]["region"]
BUCKET_NAME = ENV_CONFIG["aws"]["bucket_name"]
CLOUD_FRONT_DOMAIN = ENV_CONFIG["cloudfront"]["domain"]

# 共通の設定
ERROR_LOG = CONFIG["files"]["outputs"]["error_logs"]

DELETE_URL_LIST = CONFIG["files"]["inputs"]["delete_url_list"]
DELETE_RESULT = CONFIG["files"]["outputs"]["delete_results"]

UPLOAD_FILE_LIST = CONFIG["files"]["inputs"]["upload_file_list"]
RESOURCE = CONFIG["files"]["inputs"]["resource"]
UPLOAD_RESULT = CONFIG["files"]["outputs"]["upload_results"]

# 確認用
print(f"Using {ENVIRONMENT} environment")
print(f"Bucket Name: {BUCKET_NAME}")
