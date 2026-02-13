import json
import subprocess
from pathlib import Path


class HelmService:
    def __init__(self, helm_binary: str = "helm"):
        self.helm_binary = helm_binary

    def upgrade_install(
        self,
        release_name: str,
        namespace: str,
        chart_path: str,
        values: dict,
        timeout_seconds: int,
    ) -> None:
        cmd = [
            self.helm_binary,
            "upgrade",
            "--install",
            release_name,
            str(Path(chart_path)),
            "-n",
            namespace,
            "--create-namespace",
            "-f",
            "-",
            "--wait",
            "--timeout",
            f"{timeout_seconds}s",
        ]
        self._run(cmd, stdin_payload=json.dumps(values), timeout_seconds=timeout_seconds + 30)

    def uninstall(self, release_name: str, namespace: str, timeout_seconds: int) -> None:
        cmd = [
            self.helm_binary,
            "uninstall",
            release_name,
            "-n",
            namespace,
            "--wait",
            "--timeout",
            f"{timeout_seconds}s",
        ]
        self._run(cmd, timeout_seconds=timeout_seconds + 30)

    def _run(self, cmd: list[str], stdin_payload: str | None = None, timeout_seconds: int | None = None) -> None:
        try:
            process = subprocess.run(
                cmd,
                input=stdin_payload,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Helm command timed out after {timeout_seconds}s: {' '.join(cmd)}") from exc
        if process.returncode != 0:
            stderr = process.stderr.strip()
            stdout = process.stdout.strip()
            raise RuntimeError(f"Helm command failed: {' '.join(cmd)}\nstdout: {stdout}\nstderr: {stderr}")
