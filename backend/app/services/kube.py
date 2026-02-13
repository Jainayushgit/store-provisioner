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
