from types import SimpleNamespace

from app.services.kube import KubeService


def test_read_secret_value_decodes_base64(monkeypatch):
    service = KubeService(kubectl_binary="kubectl")

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout='{"data":{"wordpress-password":"c2VjcmV0MTIz"}}', stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    value = service.read_secret_value("store-1", "store-1", "wordpress-password")
    assert value == "secret123"


def test_read_secret_value_raises_when_key_missing(monkeypatch):
    service = KubeService(kubectl_binary="kubectl")

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout='{"data":{}}', stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    try:
        service.read_secret_value("store-1", "store-1", "wordpress-password")
    except RuntimeError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
