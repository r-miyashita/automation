import yaml

# 設定ファイルを読み込む
CONFIG_FILE = "config.yaml"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# 設定をロード
CONFIG = load_config()

# 現在の環境設定を取得
ENVIRONMENT = CONFIG["environment"]

# 環境に応じた設定を取得
if ENVIRONMENT not in CONFIG["environments"]:
    raise ValueError(f"Invalid ENVIRONMENT value: {ENVIRONMENT}")

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

# 確認用
print(f"Using {ENVIRONMENT} environment")
print(f"Bucket Name: {BUCKET_NAME}")
