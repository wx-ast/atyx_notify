import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests


@pytest.fixture
def action():
    path = Path(__file__).resolve().parents[1] / "notify.py"
    spec = importlib.util.spec_from_file_location("atyx_notification_action", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sends_token_to_current_endpoint(action, monkeypatch):
    monkeypatch.delenv("NOTIFY_BASEURL", raising=False)
    api = action.NotifyApi("key", "secret")
    data = {"message": "hello"}
    with patch.object(api.session, "post") as post, patch.object(api, "_timestamp", return_value=123):
        api.send_message("hello")
    post.assert_called_once_with("https://notify.atyx.ru/notify/", json=data, timeout=(5, 20), allow_redirects=False)
    signature = api._get_signature(123, api.baseurl, "post", api._get_contenthash(data))
    assert {k: v for k, v in api.session.headers.items() if k.startswith("X-ATYX-")} == {
        "X-ATYX-TOKEN": f"key:123:{signature}"
    }


def test_endpoint_override(action, monkeypatch):
    monkeypatch.setenv("NOTIFY_BASEURL", "https://example.test/notify/")
    assert action.NotifyApi("key", "secret").baseurl == "https://example.test/notify/"


@pytest.mark.parametrize("http_status, payload, expected", [
    (200, {"status": "ok"}, 0),
    (503, {"status": "ok"}, 1),
    (200, {"status": "error", "errors": ["message not sent"]}, 1),
    (200, [], 1),
])
def test_exit_status(action, monkeypatch, http_status, payload, expected):
    for key, value in {"API_KEY": "key", "API_SECRET": "secret", "MESSAGE": "hello"}.items():
        monkeypatch.setenv(key, value)
    response = Mock(status_code=http_status)
    response.json.return_value = payload
    with patch.object(action.NotifyApi, "send_message", return_value=response):
        assert action.main() == expected


def test_network_failure(action, monkeypatch):
    for key in ("API_KEY", "API_SECRET", "MESSAGE"):
        monkeypatch.setenv(key, "value")
    with patch.object(action.NotifyApi, "send_message", side_effect=requests.Timeout):
        assert action.main() == 1


def test_signature_excludes_port_and_query(action):
    api = action.NotifyApi("key", "secret")
    contenthash = api._get_contenthash({"message": "hello"})
    assert api._get_signature(123, "https://notify.atyx.ru:8443/notify/?a=1", "post", contenthash) == api._get_signature(
        123, "https://notify.atyx.ru/notify/", "post", contenthash
    )
