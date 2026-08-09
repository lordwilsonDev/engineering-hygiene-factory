"""Security Hygiene Skill Runner — executes mutations, collects evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mutations.base import MutationPlugin, MutationResult, RecoveryResult
from mutations.h06_audit_tampering import AuditTamperingPlugin
from mutations.h09_dependency_removal import DependencyRemovalPlugin
from mutations.h10_payload_overflow import PayloadOverflowPlugin
from mutations.h11_auth_bypass import AuthBypassPlugin
from recovery.strategies import STRATEGIES
from claims import load_claims, save_claims


class SecurityHygieneRunner:
    def __init__(self, target_path: str) -> None:
        self.target_path = Path(target_path).resolve()
        self.skill_dir = Path(__file__).parent
        self.claims = load_claims()
        self.results: list[MutationResult] = []

    def run_mutation(self, mutation: MutationPlugin, target: dict[str, Any]) -> MutationResult | None:
        print(f"\n🧪 {mutation.mutation_id} (risk={mutation.risk_level})")
        if not mutation.preconditions(target):
            print("   ⚠️ Preconditions not met, skipping")
            return None

        result = mutation.apply(target)
        print(f"   success={result.success} detected={result.observation.get('detected', 'n/a')}")
        for log in result.logs:
            print(f"   | {log}")

        if result.recovery_action:
            strategy = STRATEGIES.get(result.recovery_action)
            if strategy:
                rec = strategy.recover(target)
                print(f"   🔧 recovery={rec.get('success')} restored={rec.get('state_restored')}")
                result.recovered = bool(rec.get("success"))
                result.recovery_action = f"{result.recovery_action}:{rec.get('success')}"

        self._update_claims(result, mutation.claim_ids)
        self.results.append(result)
        return result

    def _update_claims(self, result: MutationResult, claim_ids: list[str]) -> None:
        for claim in self.claims:
            if claim["id"] in claim_ids and result.success:
                claim["status"] = "TESTED"
                claim.setdefault("evidence_refs", []).extend(result.evidence_refs)
            elif claim["id"] in claim_ids:
                claim["status"] = "FALSIFIED"
                claim.setdefault("evidence_refs", []).extend(result.evidence_refs)

    def run(self, target_config: dict[str, Any]) -> None:
        target = {
            "path": str(self.target_path),
            "url": target_config.get("url", "http://localhost:8766"),
            "headers": target_config.get("headers", {}),
            "audit_path": str(self.target_path / "audit_chain.json"),
        }

        print("\n🔐 SECURITY HYGIENE")
        print("=" * 60)
        print(f"target={target['path']} url={target['url']}")

        mutations: list[MutationPlugin] = [
            AuthBypassPlugin(),
            AuditTamperingPlugin(),
            PayloadOverflowPlugin(),
            DependencyRemovalPlugin(),
        ]

        for mutation in mutations:
            self.run_mutation(mutation, target)

        print("\n📋 CLAIM STATUS")
        for claim in self.claims:
            print(f"  {claim['id']}: {claim['status']} — {claim['statement'][:60]}")

        self._emit_evidence()

    def _emit_evidence(self) -> None:
        out = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "target": str(self.target_path),
            "results": [
                {
                    "mutation_id": r.observation.get("mutation", r.recovery_action),
                    "success": r.success,
                    "observation": r.observation,
                    "recovery": r.recovery_action,
                    "logs": r.logs,
                }
                for r in self.results
            ],
            "claims": self.claims,
        }
        out_path = self.skill_dir / "reports" / f"security_run_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2))
        print(f"\n📄 {out_path}")
        save_claims(self.claims)


def main() -> int:
    parser = argparse.ArgumentParser(description="Security Hygiene Skill Runner")
    parser.add_argument("--target", required=True, help="Target project path")
    parser.add_argument('--url', default='http://localhost:8766', help='MCP server URL')
    args = parser.parse_args()

    runner = SecurityHygieneRunner(args.target)
    runner.run({"url": args.url, "headers": {}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
