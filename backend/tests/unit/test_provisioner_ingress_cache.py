from app.core.config import Settings
from app.workers.provisioner import ProvisioningWorker


def _worker(**settings_overrides) -> ProvisioningWorker:
    settings = Settings(**settings_overrides)
    return ProvisioningWorker(settings)


def test_cache_enabled_sets_nginx_class_and_annotations():
    worker = _worker(
        store_ingress_class="nginx",
        store_guest_cache_enabled=True,
        store_guest_cache_zone="store_cache",
        store_guest_cache_ttl_seconds=14400,
    )

    ingress = worker._build_store_ingress_values("store-abc.localtest.me")

    assert ingress["ingressClassName"] == "nginx"
    annotations = ingress["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/proxy-buffering"] == "on"
    assert "proxy_cache store_cache;" in annotations["nginx.ingress.kubernetes.io/configuration-snippet"]


def test_cache_disabled_omits_annotations():
    worker = _worker(
        store_ingress_class="nginx",
        store_guest_cache_enabled=False,
    )

    ingress = worker._build_store_ingress_values("store-abc.localtest.me")

    assert ingress["ingressClassName"] == "nginx"
    assert "annotations" not in ingress


def test_cache_ttl_is_rendered_in_seconds():
    worker = _worker(
        store_guest_cache_enabled=True,
        store_guest_cache_ttl_seconds=14400,
    )

    annotations = worker._build_store_cache_annotations()
    snippet = annotations["nginx.ingress.kubernetes.io/configuration-snippet"]
    assert "proxy_cache_valid 200 301 302 14400s;" in snippet


def test_store_hostname_generation_remains_stable():
    worker = _worker(local_domain="localtest.me")

    host = worker._build_store_host("1234")
    ingress = worker._build_store_ingress_values(host)

    assert host == "store-1234.localtest.me"
    assert ingress["hostname"] == "store-1234.localtest.me"
