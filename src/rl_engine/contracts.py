from datetime import datetime
from typing import Any

from .errors import ContractError


def _fail(message: str) -> None:
    raise ContractError(message)


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{name} must be an object")
    return value


def _required(value: dict[str, Any], fields: set[str], name: str) -> None:
    missing = sorted(fields - value.keys())
    if missing:
        _fail(f"{name} missing required fields: {', '.join(missing)}")


def _exact_keys(value: dict[str, Any], required: set[str], optional: set[str], name: str) -> None:
    _required(value, required, name)
    extra = sorted(value.keys() - required - optional)
    if extra:
        _fail(f"{name} has unknown fields: {', '.join(extra)}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{name} must be a non-empty string")
    return value


def _sha(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        _fail(f"{name} must be a lowercase SHA-256")


def _timestamp(value: Any, name: str) -> None:
    _text(value, name)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} must be an ISO-8601 timestamp") from exc


def _artifact(value: Any, name: str) -> None:
    obj = _object(value, name)
    _exact_keys(obj, {"phase", "path", "sha256"}, set(), name)
    if obj["phase"] not in {"phase1", "phase2", "phase3", "phase4"}:
        _fail(f"{name}.phase is invalid")
    _text(obj["path"], f"{name}.path")
    _sha(obj["sha256"], f"{name}.sha256")


def _validate_report(instance: dict[str, Any]) -> None:
    required = {
        "schema_version", "report_status", "run_id", "incident_id", "correlation_id",
        "completed_at", "matching_context", "phase3_analysis", "phase4_outcome", "artifact_manifest"
    }
    _exact_keys(instance, required, set(), "report")
    if instance["schema_version"] != "phase4.solution-report.v1" or instance["report_status"] != "FINAL":
        _fail("report must be phase4.solution-report.v1 with report_status=FINAL")
    for field in ("run_id", "incident_id", "correlation_id"):
        _text(instance[field], field)
    _timestamp(instance["completed_at"], "completed_at")

    context = _object(instance["matching_context"], "matching_context")
    context_required = {"system", "environment", "target_service", "incident_class", "symptoms"}
    _exact_keys(context, context_required, {"software_versions"}, "matching_context")
    for field in ("system", "environment", "target_service", "incident_class"):
        _text(context[field], f"matching_context.{field}")
    symptoms = context["symptoms"]
    if not isinstance(symptoms, list) or not symptoms or len(symptoms) != len(set(symptoms)):
        _fail("matching_context.symptoms must be a non-empty unique string list")
    for item in symptoms:
        _text(item, "matching_context.symptoms[]")
    versions = context.get("software_versions", {})
    if not isinstance(versions, dict):
        _fail("matching_context.software_versions must be an object")
    for key, value in versions.items():
        _text(key, "software_versions key")
        _text(value, f"software_versions.{key}")

    phase3 = _object(instance["phase3_analysis"], "phase3_analysis")
    _required(phase3, {"source_artifact", "observations", "technical_solution"}, "phase3_analysis")
    _artifact(phase3["source_artifact"], "phase3_analysis.source_artifact")
    if phase3["source_artifact"]["phase"] != "phase3":
        _fail("phase3_analysis source artifact must belong to phase3")
    observations = phase3["observations"]
    if not isinstance(observations, list) or not observations:
        _fail("phase3_analysis.observations must be a non-empty list")
    for item in observations:
        _text(item, "phase3_analysis.observations[]")
    solution = _object(phase3["technical_solution"], "phase3_analysis.technical_solution")
    _required(solution, {"consensus_rc", "primary_component", "action_commands", "calculated_confidence", "safety_violation"}, "technical_solution")
    _text(solution["consensus_rc"], "technical_solution.consensus_rc")
    _text(solution["primary_component"], "technical_solution.primary_component")
    commands = solution["action_commands"]
    if not isinstance(commands, list) or not commands:
        _fail("technical_solution.action_commands must be a non-empty list")
    for command in commands:
        _text(command, "technical_solution.action_commands[]")
    confidence = solution["calculated_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100:
        _fail("technical_solution.calculated_confidence must be between 0 and 100")
    if not isinstance(solution["safety_violation"], bool):
        _fail("technical_solution.safety_violation must be boolean")

    phase4 = _object(instance["phase4_outcome"], "phase4_outcome")
    phase4_required = {
        "source_artifact", "gate_decision", "before_state", "agent_proposal", "guardrail_result",
        "execution_result", "after_state", "fault_cleared", "human_intervention_required", "performance"
    }
    _required(phase4, phase4_required, "phase4_outcome")
    _artifact(phase4["source_artifact"], "phase4_outcome.source_artifact")
    if phase4["source_artifact"]["phase"] != "phase4":
        _fail("phase4_outcome source artifact must belong to phase4")
    valid_gates = {"EXECUTED", "BLOCKED_SAFETY_VIOLATION", "BLOCKED_GUARDRAIL", "BLOCKED_UNMAPPED", "SKIPPED_NO_SUITABLE_FAULT"}
    if phase4["gate_decision"] not in valid_gates:
        _fail("phase4_outcome.gate_decision is invalid")
    if phase4["gate_decision"] == "EXECUTED":
        if not isinstance(phase4["fault_cleared"], bool) or phase4["human_intervention_required"] is not False:
            _fail("executed outcomes require boolean fault_cleared and no human intervention")
    elif phase4["fault_cleared"] is not None or phase4["human_intervention_required"] is not True:
        _fail("blocked/skipped outcomes require fault_cleared=null and human intervention")
    if not isinstance(phase4["performance"], dict):
        _fail("phase4_outcome.performance must be an object")

    manifest = instance["artifact_manifest"]
    if not isinstance(manifest, list) or len(manifest) < 2:
        _fail("artifact_manifest must contain at least Phase 3 and Phase 4 artifacts")
    for index, artifact in enumerate(manifest):
        _artifact(artifact, f"artifact_manifest[{index}]")
    if not {"phase3", "phase4"}.issubset({item["phase"] for item in manifest}):
        _fail("artifact_manifest must reference both Phase 3 and Phase 4")


def _validate_decision(instance: dict[str, Any]) -> None:
    required = {"schema_version", "run_id", "report_sha256", "decision", "actor", "decided_at"}
    _exact_keys(instance, required, {"comment"}, "decision")
    if instance["schema_version"] != "rl.user-save-decision.v1":
        _fail("decision schema_version is invalid")
    _text(instance["run_id"], "decision.run_id")
    _sha(instance["report_sha256"], "decision.report_sha256")
    if instance["decision"] not in {"SAVE", "DO_NOT_SAVE", "REVIEW_LATER"}:
        _fail("decision.decision is invalid")
    _text(instance["actor"], "decision.actor")
    _timestamp(instance["decided_at"], "decision.decided_at")


def validate(instance: dict[str, Any], schema_name: str) -> None:
    obj = _object(instance, schema_name)
    if schema_name == "phase4_solution_report_v1.schema.json":
        _validate_report(obj)
    elif schema_name == "user_save_decision_v1.schema.json":
        _validate_decision(obj)
    elif schema_name == "saved_approach_v1.schema.json":
        required = {
            "schema_version", "approach_id", "run_id", "incident_id", "fingerprint_sha256",
            "matching_context", "phase3_solution", "phase4_verification", "source_report_sha256",
            "saved_by", "saved_at", "status"
        }
        _exact_keys(obj, required, set(), "saved approach")
        if obj["schema_version"] != "rl.saved-approach.v1" or obj["status"] != "VALIDATED":
            _fail("saved approach version or status is invalid")
        for field in ("approach_id", "run_id", "incident_id", "saved_by"):
            _text(obj[field], f"saved approach.{field}")
        _sha(obj["fingerprint_sha256"], "saved approach.fingerprint_sha256")
        _sha(obj["source_report_sha256"], "saved approach.source_report_sha256")
        _timestamp(obj["saved_at"], "saved approach.saved_at")
    elif schema_name == "sync_envelope_v1.schema.json":
        required = {"schema_version", "event_id", "event_type", "run_id", "created_at", "payload_sha256", "payload"}
        _exact_keys(obj, required, set(), "sync envelope")
        if obj["schema_version"] != "rl.sync-envelope.v1" or obj["event_type"] not in {"APPROACH_SAVED", "USER_DECISION_RECORDED"}:
            _fail("sync envelope version or event_type is invalid")
        for field in ("event_id", "run_id"):
            _text(obj[field], f"sync envelope.{field}")
        _timestamp(obj["created_at"], "sync envelope.created_at")
        _sha(obj["payload_sha256"], "sync envelope.payload_sha256")
        _object(obj["payload"], "sync envelope.payload")
    else:
        _fail(f"unknown contract: {schema_name}")
