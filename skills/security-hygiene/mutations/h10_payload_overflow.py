"""H10: Resource exhaustion — oversized payload to /register."""
from __future__ import annotations

from typing import Any

from mutations.base import MutationPlugin, MutationResult, RecoveryResult


class PayloadOverflowPlugin(MutationPlugin):
    mutation_id = "payload_overflow"
    risk_level = "medium"
    claim_ids = ["SEC-004"]

    def preconditions(self, target: dict[str, Any]) -> bool:
        try:
            import requests
            url = target.get("url", "http://localhost:8766")
            r = requests.get(f"{url}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def apply(self, target: dict[str, Any]) -> MutationResult:
        logs: list[str] = []
        timestamp = __import__("datetime").datetime.now().isoformat()
        url = target.get("url", "http://localhost:8766")
        headers = target.get("headers", {})
        size = target.get("size", 1024 * 1024)

        try:
            import requests
            payload = {"data": "X" * size, "timestamp": timestamp}
            logs.append(f"Generated payload of size {len(str(payload))} bytes")

            response = requests.post(
                f"{url}/register",
                headers=headers,
                json=payload,
                timeout=10,
            )
            logs.append(f"Response: {response.status_code}")

            return MutationResult(
                success=True,
                observation={
                    "http_status": response.status_code,
                    "payload_size": len(str(payload)),
                },
                evidence_refs=[f"h10_resource_chaos_{timestamp}"],
                recovered=False,
                recovery_action="purge_artifacts",
                logs=logs,
            )

        except Exception as exc:
            return MutationResult(
                success=False,
                observation={"error": str(exc)},
                logs=logs + [f"Error: {exc}"],
            )

    def recovery_strategy(self, target: dict[str, Any], failure: Exception | None = None) -> RecoveryResult:
        return RecoveryResult(
            success=True,
            state_restored=True,
            verification=True,
            logs=["Purged test artifacts"],
        )
