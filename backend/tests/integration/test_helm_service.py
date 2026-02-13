from types import SimpleNamespace

from app.services.helm import HelmService


def test_upgrade_install_raises_runtime_error_on_failure(monkeypatch):
    service = HelmService(helm_binary="helm")

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("subprocess.run", fake_run)

    try:
        service.upgrade_install(
            release_name="store-1",
            namespace="store-1",
            chart_path="./charts/woocommerce",
            values={"key": "value"},
            timeout_seconds=10,
        )
    except RuntimeError as exc:
        assert "Helm command failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
