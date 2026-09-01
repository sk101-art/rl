import hashlib
import json
import re
from typing import Any


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def build_fingerprint(context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    normalized = {
        "system": _normalize(context["system"]),
        "environment": _normalize(context["environment"]),
        "target_service": _normalize(context["target_service"]),
        "incident_class": _normalize(context["incident_class"]),
        "symptoms": sorted({_normalize(item) for item in context["symptoms"]}),
        "software_versions": {
            _normalize(key): _normalize(value)
            for key, value in sorted(context.get("software_versions", {}).items())
        },
    }
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), normalized
