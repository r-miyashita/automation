import errno
import logging
from unittest.mock import Mock, patch, MagicMock, mock_open, call

import pytest
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
)

from s3_operations.utils import (
    create_s3_client,
    log_auth_error,
    log_client_error,
    log_default_error,
    log_file_error,
    is_url_accessible,
    write_results_to_file
)


@pytest.mark.parametrize(
    "error_response, expected_message",
    [
        # 403エラー: アクセス権限不足
        (
            {"Error": {"Code": "403", "Message": "Access Denied"}},
            "クライアントエラー（認証失敗またはアクセス権限不足）： Access Denied",
        ),
        # 404エラー: バケットが見つからない
        (
            {"Error": {"Code": "404", "Message": "Bucket Not Found"}},
            "クライアントエラー（バケットが不明）： Bucket Not Found",
        ),
        # その他のエラー
        (
            {"Error": {"Code": "500", "Message": "Internal Server Error"}},
            "クライアントエラー（未定義のエラー）： Internal Server Error",
        ),
    ],
)
def test_log_client_error(caplog, error_response, expected_message):
    # `ClientError`をモック化
    mock_client_error = Mock(spec=ClientError)
    mock_client_error.response = error_response

    # ログキャプチャ開始
    with caplog.at_level(logging.ERROR):
        # `log_client_error`を呼び出す
        log_client_error(mock_client_error)

    # 期待するエラーメッセージがログに含まれているかを確認
    assert expected_message in caplog.text


@pytest.mark.parametrize(
    "error_instance, expected_message",
    [
        # NoCredentialsError
        (NoCredentialsError(), "認証エラー: Unable to locate credentials"),
        # PartialCredentialsError
        (
            PartialCredentialsError(
                provider="AWS_ACCESS_KEY_ID", cred_var="AWS_SECRET_ACCESS_KEY"
            ),
            "認証エラー: Partial credentials found in AWS_ACCESS_KEY_ID, missing: AWS_SECRET_ACCESS_KEY",
        ),
    ],
)
def test_log_auth_error(caplog, error_instance, expected_message):
    # ログキャプチャ開始
    with caplog.at_level(logging.ERROR):
        # 'log_auth_error'を呼び出す
        log_auth_error(error_instance)

    print("\n")
    print(f"caplog: {caplog.text}")

    # 期待するメッセージがログに含まれているかを確認
    assert expected_message in caplog.text


@pytest.mark.parametrize(
    "error_instance, expected_message",
    [
        # FileNotFoundError
        (
            FileNotFoundError(errno.ENOENT, "No such file or directory", "missing.txt"),
            "指定されたファイルが見つかりません： [Errno 2] No such file or directory: 'missing.txt'",
        )
    ],
)
def test_log_file_error(caplog, error_instance, expected_message):
    # ログキャプチャ開始
    with caplog.at_level(logging.ERROR):
        # 'log_file_error'を呼び出す
        log_file_error(error_instance)

    print("\n")
    print(f"caplog: {caplog.text}")

    # 期待するメッセージがログに含まれているかを確認
    assert expected_message in caplog.text


@pytest.mark.parametrize(
    "raise_func, context, expected_type, expected_message_part",
    [
        (lambda: 1 / 0, "除算処理", "ZeroDivisionError", "division by zero"),
        (
            lambda: int("abc"),
            "文字列変換処理",
            "ValueError",
            "invalid literal for int()",
        ),
    ],
)
def test_log_default_error(
    raise_func, context, expected_type, expected_message_part, caplog
):
    try:
        raise_func()
    except Exception as e:
        with caplog.at_level(logging.ERROR):
            log_default_error(e, context)

        # ログが出力されていることを確認
        assert len(caplog.records) > 0
        print("\n")
        print(caplog.text)
        assert expected_message_part in caplog.text
        assert expected_type in caplog.text


@patch("s3_operations.utils.boto3.client", return_value=Mock(name="mock_s3"))
def test_create_s3_client_success(mock_boto3_client):
    s3_client = create_s3_client()

    # メソッド内でモックが呼び出されることを確認
    assert s3_client is mock_boto3_client.return_value
    mock_boto3_client.assert_called_once()


@pytest.mark.parametrize(
    "side_effect, expected_log, expected_client",
    [
        # 特定エラー用のルート確認
        (NoCredentialsError, "log_auth_error", None),
        # その他エラー用のルート確認
        (EndpointConnectionError, "log_default_error", None),
    ],
)
def test_create_s3_client_error_handling(side_effect, expected_log, expected_client):
    with (
        # パラメータから渡されるside_effectを設定
        patch(
            "s3_operations.utils.boto3.client", side_effect=side_effect
        ) as mock_boto3_client,
        # expected_logに対応するモックを用意
        # （ nameを明示的に指定するために、@patchではなくwith句で設定している ）
        patch("s3_operations.utils.log_auth_error") as mock_log_auth_error,
        patch("s3_operations.utils.log_default_error") as mock_log_default_error,
    ):
        _ = mock_boto3_client

        s3_client = create_s3_client()

        # 戻り値の確認
        assert s3_client is expected_client

        # logHandlingが適切であることの確認
        if expected_log == "log_auth_error":
            mock_log_auth_error.assert_called_once()
        elif expected_log == "log_default_error":
            mock_log_default_error.assert_called_once()

@patch("s3_operations.utils.request.urlopen")
def test_is_url_accessible_success(mock_urlopen):
    url = "https://dummy.com"
    
    # responseをモック化しレスポンスステータスをセット
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    
    # mock_urlopenにレスポンスをセット
    mock_urlopen.return_value = mock_response
    
    is_accessible = is_url_accessible(url)
    
    assert is_accessible is True

@patch("s3_operations.utils.request.urlopen")
def test_is_url_accessible_failure(mock_urlopen):
    url = "https://dummy.com"
    
    # responseをモック化しレスポンスステータスをセット
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 404
    
    # mock_urlopenにレスポンスをセット
    mock_urlopen.return_value = mock_response
    
    is_accessible = is_url_accessible(url)
    
    assert is_accessible is False

@pytest.mark.parametrize(
    "success_list, failure_list, expected_output",
    [
        # success_list, failure_listどちらもデータが存在する場合
        (
            ["./data/dummy1.txt", "./data/dummy2.txt",],
            [
                {"file_name":"./data/dummy3.txt","reason": "failure", "url": "https://dummy.com/data/dummy3.txt"},
                {"file_name":"./data/dummy4.txt","reason": "failure", "url": "https://dummy.com/data/dummy4.txt"},
            ],
            [
                "成功 ####\n",
                "./data/dummy1.txt\n",
                "./data/dummy2.txt\n",
                "\n",
                "失敗 ####\n",
                "[./data/dummy3.txt] failure : https://dummy.com/data/dummy3.txt\n",
                "[./data/dummy4.txt] failure : https://dummy.com/data/dummy4.txt\n",
            ]
            
        ),
        
        # 中身が全て空の場合
        ([],[], ["成功 ####\n", "\n", "失敗 ####\n",])
    ]
)
@patch("builtins.print")
def test_write_result_to_file_success(mock_print, success_list, failure_list, expected_output):
    # write検証用にモック（ mock_open() ）を生成しパッチに渡す
    with patch("builtins.open", mock_open()) as m:
        dummy_file = "./dummy.txt"    
        write_results_to_file(success_list, failure_list, output_file=dummy_file)
        
        handle = m()
        
        # writeの内容を確認
        handle.write.assert_has_calls(

            # 期待されるcallオブジェクトのリストを生成
            [call(line) for line in expected_output],
            
            # 順番まで担保する
            any_order=False
        )

        # メッセージの出力を確認
        mock_print.assert_called_with(f"結果を{dummy_file}に出力しました")


@patch("s3_operations.utils.log_default_error")
@patch("builtins.print")
@patch("builtins.open", side_effect=FileNotFoundError)
def test_write_result_to_file_with_exception(mock_open, mock_print, mock_log_handler):
    success_list = []
    failure_list = []
    write_results_to_file(success_list,failure_list, output_file="./dummy.txt")
    
    # logが呼び出されることを確認
    mock_log_handler.assert_called_once()
    
    # # メッセージの出力を確認
    mock_print.assert_called_once()
    assert mock_print.call_args[0][0].startswith("結果ファイルの出力に失敗しました。")