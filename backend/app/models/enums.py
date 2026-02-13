import enum


class StoreEngine(str, enum.Enum):
    WOOCOMMERCE = "woocommerce"
    MEDUSA = "medusa"


class StoreStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"
    DELETED = "DELETED"


class JobAction(str, enum.Enum):
    PROVISION = "PROVISION"
    DELETE = "DELETE"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
