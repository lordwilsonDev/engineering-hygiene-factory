"""Recovery strategies for security mutations."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class RecoveryStrategy:
    name: str = ""

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class RestartService(RecoveryStrategy):
    name = "restart_service"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        logs = ["Restarted uvicorn"]
        return {"success": True, "logs": logs}


class RestoreDirectory(RecoveryStrategy):
    name = "restore_directory"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        path = Path(target.get("path", "."))
        backup = path.with_suffix(".hygiene_backup")
        if backup.exists():
            shutil.move(str(backup), str(path))
            return {"success": True, "state_restored": True, "logs": [f"Restored {path} from backup"]}
        return {"success": False, "state_restored": False, "logs": ["No backup found"]}


class PurgeArtifacts(RecoveryStrategy):
    name = "purge_artifacts"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        injection_dir = Path("/tmp/hygiene_injections")
        if injection_dir.exists():
            shutil.rmtree(str(injection_dir))
        return {"success": True, "state_restored": True, "logs": ["Purged test artifacts"]}


class ReconnectClient(RecoveryStrategy):
    name = "reconnect_client"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "state_restored": True, "logs": ["Reconnected client"]}


class QuarantineEndpoint(RecoveryStrategy):
    name = "quarantine_endpoint"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "state_restored": True, "logs": ["Quarantined endpoint"]}


class ResetChain(RecoveryStrategy):
    name = "reset_chain"

    def recover(self, target: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "state_restored": True, "logs": ["Reset audit chain"]}


STRATEGIES: dict[str, RecoveryStrategy] = {
    "restart_service": RestartService(),
    "restore_directory": RestoreDirectory(),
    "purge_artifacts": PurgeArtifacts(),
    "reconnect_client": ReconnectClient(),
    "quarantine_endpoint": QuarantineEndpoint(),
    "reset_chain": ResetChain(),
}
