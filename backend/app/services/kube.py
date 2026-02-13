import base64
import json
import subprocess


class KubeService:
    def __init__(self, kubectl_binary: str = "kubectl", delete_timeout_seconds: int = 180):
        self.kubectl_binary = kubectl_binary
        self.delete_timeout_seconds = delete_timeout_seconds

    def delete_namespace(self, namespace: str) -> None:
        cmd = [
            self.kubectl_binary,
            "delete",
            "namespace",
            namespace,
            "--ignore-not-found=true",
            "--wait=true",
            f"--timeout={self.delete_timeout_seconds}s",
        ]
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            stderr = process.stderr.strip()
            stdout = process.stdout.strip()
            raise RuntimeError(f"kubectl delete namespace failed\nstdout: {stdout}\nstderr: {stderr}")

    def read_secret_value(self, namespace: str, secret_name: str, key: str) -> str:
        cmd = [self.kubectl_binary, "get", "secret", secret_name, "-n", namespace, "-o", "json"]
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            stderr = process.stderr.strip()
            stdout = process.stdout.strip()
            raise RuntimeError(f"kubectl get secret failed\nstdout: {stdout}\nstderr: {stderr}")

        try:
            payload = json.loads(process.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("kubectl get secret returned invalid JSON") from exc

        encoded_value = payload.get("data", {}).get(key)
        if not encoded_value:
            raise RuntimeError(f"Secret key '{key}' not found in '{secret_name}'")

        try:
            return base64.b64decode(encoded_value).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to decode secret '{secret_name}' key '{key}'") from exc
