from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "store-provisioner"
    environment: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/platform"

    worker_id: str = "worker-1"
    worker_poll_seconds: float = 2.0
    worker_lease_seconds: int = 180
    worker_max_concurrency: int = 2
    worker_max_attempts: int = 3

    helm_binary: str = "helm"
    kubectl_binary: str = "kubectl"
    kubectl_delete_timeout_seconds: int = 180
    helm_chart_path: str = "./charts/woocommerce"
    helm_timeout_seconds: int = 300

    local_domain: str = "localtest.me"
    http_ready_timeout_seconds: int = 240
    http_ready_poll_seconds: int = 5

    default_store_engine: str = "woocommerce"

    rate_limit_window_seconds: int = 60
    rate_limit_create_delete_per_window: int = 15
    max_active_stores: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
