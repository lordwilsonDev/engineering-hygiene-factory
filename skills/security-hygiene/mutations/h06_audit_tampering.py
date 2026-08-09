"""H06: Audit chain tampering detection."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from mutations.base import MutationPlugin, MutationResult, RecoveryResult


class AuditTamperingPlugin(MutationPlugin):
    mutation_id = "audit_chain_tampering"
    risk_level = "high"
    claim_ids = ["SEC-002", "SEC-003"]

    def preconditions(self, target: dict[str, Any]) -> bool:
        audit_path = Path(target.get("audit_path", "./audit_chain.json"))
        return audit_path.exists() and os.path.getsize(str(audit_path)) > 0

    def apply(self, target: dict[str, Any]) -> MutationResult:
        logs: list[str] = []
        audit_path = Path(target.get("audit_path", "./audit_chain.json"))
        timestamp = __import__("datetime").datetime.now().isoformat()

        try:
            with open(audit_path, "r") as f:
                chain = json.load(f)

            logs.append(f"Read audit chain: {len(chain)} entries")

            if not chain:
                return MutationResult(
                    success=False,
                    observation={"error": "Empty audit chain"},
                    logs=logs + ["Empty chain - nothing to tamper"],
                )

            # Tamper with an entry but keep original checksum
            original = dict(chain[0])
            chain[0]["data"] = f"TAMPERED_{timestamp}"
            logs.append("Tampered entry 0 text, kept original checksum")

            tampered_path = audit_path.with_suffix(".hygiene_tampered.json")
            with open(tampered_path, "w") as f:
                json.dump(chain, f, indent=2)

            # Verify detection via the msb_v3.uac.audit_chain.AuditChain verify method
            detected = False
            try:
                import importlib.util, sys
                spec = importlib.util.spec_from_file_location("audit_chain", target.get("audit_module_path", ""))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["audit_chain"] = mod
                    spec.loader.exec_module(mod)
                    chain_obj = mod.AuditChain(str(audit_path))
                    detected = bool(chain_obj.verify())
            except Exception as exc:
                logs.append(f"Detection probe error: {exc}")

            return MutationResult(
                success=True,
                observation={
                    "tampered": True,
                    "detected": detected,
                    "entry_count": len(chain),
                },
                evidence_refs=[f"h06_audit_tampering_{timestamp}"],
                recovered=False,
                recovery_action="reset_chain",
                logs=logs,
            )

        except Exception as exc:
            return MutationResult(
                success=False,
                observation={"error": str(exc)},
                logs=logs + [f"Error: {exc}"],
            )

    def recovery_strategy(self, target: dict[str, Any], failure: Exception | None = None) -> RecoveryResult:
        audit_path = Path(target.get("audit_path", "./audit_chain.json"))
        tampered_path = audit_path.with_suffix(".hygiene_tampered.json")
        backup_path = audit_path.with_suffix(".hygiene_backup")

        source = backup_path if backup_path.exists() else tampered_path
        if source.exists():
            import shutil
            shutil.move(str(source), str(audit_path))
            return RecoveryResult(
                success=True,
                state_restored=True,
                verification=True,
                logs=[f"Restored audit chain from {source.name}"],
            )

        return RecoveryResult(success=False, state_restored=False, verification=False, logs=["No backup found"])
