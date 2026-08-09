"""H09: Dependency subtraction — remove non-builtin dependency, observe graceful degradation."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from mutations.base import MutationPlugin, MutationResult, RecoveryResult


class DependencyRemovalPlugin(MutationPlugin):
    mutation_id = "dependency_removal"
    risk_level = "medium"
    claim_ids = ["SEC-005"]

    def preconditions(self, target: dict[str, Any]) -> bool:
        dep_dir = Path(target.get("dependency_dir", "./vendor"))
        return dep_dir.exists() and any(dep_dir.iterdir())

    def apply(self, target: dict[str, Any]) -> MutationResult:
        logs: list[str] = []
        dep_dir = Path(target.get("dependency_dir", "./vendor"))
        timestamp = __import__("datetime").datetime.now().isoformat()

        if not dep_dir.exists():
            return MutationResult(
                success=False,
                observation={"error": f"Dependency directory not found: {dep_dir}"},
                logs=logs + ["Precondition failed"],
            )

        # Move directory to backup
        backup = dep_dir.with_suffix(".hygiene_backup")
        shutil.move(str(dep_dir), str(backup))
        logs.append(f"Moved {dep_dir} -> {backup}")

        return MutationResult(
            success=True,
            observation={"dependency_dir_removed": True, "backup_path": str(backup)},
            evidence_refs=[f"h09_dependency_removal_{timestamp}"],
            recovered=False,
            recovery_action="restore_directory",
            logs=logs,
        )

    def recovery_strategy(self, target: dict[str, Any], failure: Exception | None = None) -> RecoveryResult:
        dep_dir = Path(target.get("dependency_dir", "./vendor"))
        backup = dep_dir.with_suffix(".hygiene_backup")
        if backup.exists() and not dep_dir.exists():
            shutil.move(str(backup), str(dep_dir))
            return RecoveryResult(
                success=True,
                state_restored=True,
                verification=dep_dir.exists(),
                logs=[f"Restored {dep_dir} from backup"],
            )
        return RecoveryResult(success=True, state_restored=True, verification=True, logs=["No action needed"])
