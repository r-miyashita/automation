import pytest
from unittest.mock import patch, mock_open
from config import load_config  # config.pyのload_configをインポート


# ----------------------------------
# load_config()
# ----------------------------------
# ✅ Normal-Test >>>>>>>>>

mock_yaml_content = """
environment: dev
environments:
  dev:
    aws:
      access_key_id: "fake-access-key-id"
      secret_access_key: "fake-secret-access-key"
  prod:
    aws:
      access_key_id: "prod-access-key-id"
      secret_access_key: "prod-secret-access-key"
files:
  inputs:
    delete_url_list: "data/s3_operations/delete_url_list.txt"
  outputs:
    error_logs: "data/s3_operations/error.log"
    delete_results: "data/s3_operations/delete_results.txt"
"""

def test_load_config_success():
    """
    load_config() が正しく動くことを確認
    """
    # 設定をロード
    with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
      config = load_config()

    # 環境設定が正しいことを確認
    assert config["environment"] == "dev"
    assert config["environments"]["dev"]["aws"]["access_key_id"] == "fake-access-key-id"
    assert config["environments"]["dev"]["aws"]["secret_access_key"] == "fake-secret-access-key"
    assert config["files"]["outputs"]["error_logs"] == "data/s3_operations/error.log"



# ❌ Abnormal-Test >>>>>>>>>

# ValueError 発生ケース
mock_invalid_environment_yaml_content = """
environment: "fake-dev"
environments:
  dev:
    aws:
      access_key_id: "fake-access-key-id"
      secret_access_key: "fake-secret-access-key"
  prod:
    aws:
      access_key_id: "prod-access-key-id"
      secret_access_key: "prod-secret-access-key"
"""

def test_load_config_error():
    """
    環境設定が正しくない場合に ValueError を発生させる
    """
    with patch("builtins.open", mock_open(read_data=mock_invalid_environment_yaml_content)):
        with pytest.raises(ValueError):
            load_config()

