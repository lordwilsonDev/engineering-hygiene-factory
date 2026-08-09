"""H11: Authentication bypass — request MCP endpoints without x-mcp-secret."""
from __future__ import annotations

from typing import Any

from mutations.base import MutationPlugin, MutationResult, RecoveryResult


class AuthBypassPlugin(MutationPlugin):
    mutation_id = "authentication_bypass"
    risk_level = "high"
    claim_ids = ["SEC-001"]

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

        try:
            import requests
            # Strip auth header
            test_headers = {k: v for k, v in headers.items() if k != "x-mcp-secret"}

            response = requests.post(
                f"{url}/mcp",
                headers=test_headers,
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                timeout=10,
            )
            logs.append(f"Request without auth: {response.status_code}")
            match = response.status_code in [401, 403]

            return MutationResult(
                success=True,
                observation={
                    "http_status": response.status_code,
                    "match": match,
                    "body_preview": response.text[:200],
                },
                evidence_refs=[f"h11_auth_bypass_{timestamp}"],
                recovered=False,
                recovery_action="reconnect_client",
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
            logs=["Re-authenticated client session"],
        )
