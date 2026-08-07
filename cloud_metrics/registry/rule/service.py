"""Rule Registry service — Milestone 9.

Evaluates seeded ``cim_validation_rules`` against an orchestration context.
Returns structured ``ValidationResult`` objects; does not block ingestion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.rule.types import (
    RuleEntry,
    RuleEvaluationResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({"approved", "active"})


def _as_list(val: Any) -> List[Any]:
    if val is None:
        return []
    if isinstance(val, (list, tuple, set)):
        return list(val)
    return [val]


def _present(payload: Mapping[str, Any], field: str) -> bool:
    if field not in payload:
        return False
    v = payload.get(field)
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    if isinstance(v, (list, dict)) and len(v) == 0:
        return False
    return True


class RuleRegistryService:
    """Rule Registry with optional DB session."""

    registry_name = RegistryName.RULE
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[RuleEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimValidationRule

        rows = (
            self._session.query(CimValidationRule)
            .filter(CimValidationRule.status.in_(tuple(_ACTIVE)))
            .order_by(CimValidationRule.name.asc())
            .all()
        )
        return [self._to_entry(r) for r in rows]

    def get_by_name(self, name: str) -> Optional[RuleEntry]:
        if self._session is None or not name:
            return None
        from cloud_metrics.models.cim_registry import CimValidationRule

        row = (
            self._session.query(CimValidationRule)
            .filter_by(name=name.strip())
            .first()
        )
        return self._to_entry(row) if row else None

    def get_rules(
        self,
        *,
        target_registry: Optional[str] = None,
        metric_type: Optional[str] = None,
        domain: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[RuleEntry]:
        """Filter seeded rules; metric_type/domain/category used as soft filters."""
        rules = self.list_entries()
        out: List[RuleEntry] = []
        for rule in rules:
            if target_registry and rule.target_registry not in {
                target_registry,
                "metric",
                "extension",
            }:
                # Keep metric + extension targets when filtering orchestration
                if rule.target_registry != target_registry:
                    continue
            cond = rule.condition or {}
            when_types = _as_list(cond.get("when_metric_type"))
            if when_types and metric_type and metric_type not in when_types:
                # Still return rule — evaluate() decides applicability
                pass
            when_domain = cond.get("domain")
            if when_domain and domain and when_domain != domain:
                pass
            when_cat = cond.get("when_category")
            if when_cat and category and when_cat != category:
                pass
            out.append(rule)
        if target_registry:
            out = [
                r
                for r in out
                if r.target_registry in {target_registry, "metric", "extension"}
            ]
        return out

    def validate(self, payload: Dict[str, Any]) -> List[str]:
        """Backward-compatible string list (legacy-style)."""
        eval_res = self.evaluate(payload)
        messages: List[str] = []
        for r in eval_res.results:
            if not r.passed and r.message:
                messages.append(r.message)
        return messages

    def evaluate(
        self,
        payload: Mapping[str, Any],
        *,
        rules: Optional[Sequence[RuleEntry]] = None,
    ) -> RuleEvaluationResult:
        """Apply rules and return structured validation results."""
        rule_list = list(rules) if rules is not None else self.list_entries()
        if not rule_list and self._session is None:
            return RuleEvaluationResult()

        results: List[ValidationResult] = []
        warnings: List[str] = []
        errors: List[str] = []
        has_critical = False

        for rule in rule_list:
            if (rule.status or "active").lower() not in {"active", "approved"}:
                continue
            if not self._rule_applies(rule, payload):
                continue
            vr = self._evaluate_rule(rule, payload)
            results.append(vr)
            if vr.passed:
                continue
            msg = vr.message or f"rule failed: {rule.name}"
            if vr.severity == "critical":
                has_critical = True
                errors.append(msg)
            elif vr.severity == "error":
                errors.append(msg)
            elif vr.severity == "warning":
                warnings.append(msg)
            else:
                warnings.append(msg)

        logger.info(
            "rule evaluation: results=%d warnings=%d errors=%d critical=%s",
            len(results),
            len(warnings),
            len(errors),
            has_critical,
        )
        return RuleEvaluationResult(
            results=results,
            warnings=warnings,
            errors=errors,
            has_critical=has_critical,
        )

    def _rule_applies(self, rule: RuleEntry, payload: Mapping[str, Any]) -> bool:
        cond = rule.condition or {}
        when_types = _as_list(cond.get("when_metric_type"))
        metric_type = payload.get("metric_type")
        if when_types and metric_type not in when_types:
            return False
        when_domain = cond.get("domain")
        if when_domain and payload.get("domain") != when_domain:
            return False
        when_cat = cond.get("when_category")
        if when_cat and payload.get("category") != when_cat:
            return False
        when_stage = cond.get("when_lifecycle_stage")
        if when_stage:
            stages = payload.get("lifecycle_stages") or []
            if when_stage not in stages:
                return False
        if rule.target_registry == "extension" and not payload.get("is_extension"):
            return False
        return True

    def _evaluate_rule(
        self, rule: RuleEntry, payload: Mapping[str, Any]
    ) -> ValidationResult:
        cond = rule.condition or {}
        severity = (rule.severity or "error").lower()
        if severity not in {"info", "warning", "error", "critical"}:
            severity = "error"

        # required single field
        if cond.get("op") == "required" and cond.get("field"):
            field = cond["field"]
            ok = _present(payload, field)
            return ValidationResult(
                rule_name=rule.name,
                passed=ok,
                severity=severity,
                message=None
                if ok
                else (rule.description or f"Missing required field: {field}"),
                rule_type=rule.rule_type,
                target_registry=rule.target_registry,
                details={"field": field},
            )

        # required_unless quantity kind
        if cond.get("op") == "required_unless" and cond.get("field"):
            field = cond["field"]
            unless = set(_as_list(cond.get("unless_quantity_kind")))
            qk = payload.get("quantity_kind") or payload.get("expected_quantity_kind")
            if qk in unless or payload.get("is_dimensionless"):
                return ValidationResult(
                    rule_name=rule.name,
                    passed=True,
                    severity=severity,
                    message="not required for dimensionless",
                    rule_type=rule.rule_type,
                    target_registry=rule.target_registry,
                )
            # Map canonical_unit_id → observed_unit / canonical_unit in payload
            ok = (
                _present(payload, field)
                or _present(payload, "observed_unit")
                or _present(payload, "canonical_unit")
                or _present(payload, "unit")
            )
            return ValidationResult(
                rule_name=rule.name,
                passed=ok,
                severity=severity,
                message=None
                if ok
                else (rule.description or "Numeric metric requires a unit"),
                rule_type=rule.rule_type,
                target_registry=rule.target_registry,
                details={"field": field, "quantity_kind": qk},
            )

        # require list of fields
        require = _as_list(cond.get("require"))
        if require:
            missing = [f for f in require if not _present(payload, f)]
            # Map aliases for sample-time fields
            alias = {
                "timestamp": ["timestamp", "captured_at"],
                "source": ["source", "source_name", "source_id"],
                "formula_or_derivation_method": [
                    "formula_or_derivation_method",
                    "formula",
                    "derivation_method",
                ],
                "aggregation_period": ["aggregation_period", "reporting_period"],
                "boundary": ["boundary", "calculation_boundary"],
                "workflow_id": ["workflow_id", "workflow"],
                "run_id": ["run_id", "workflow_run_id", "workflow_run"],
            }
            still_missing = []
            for f in missing:
                alts = alias.get(f, [f])
                if any(_present(payload, a) for a in alts):
                    continue
                still_missing.append(f)
            ok = len(still_missing) == 0
            return ValidationResult(
                rule_name=rule.name,
                passed=ok,
                severity=severity,
                message=None
                if ok
                else (
                    rule.description
                    or f"Missing required fields: {', '.join(still_missing)}"
                ),
                rule_type=rule.rule_type,
                target_registry=rule.target_registry,
                details={"missing": still_missing},
            )

        # energy power vs energy consistency
        if cond.get("unit_must_match_quantity_kind"):
            qk = payload.get("quantity_kind") or payload.get("expected_quantity_kind")
            unit_status = payload.get("unit_validation_status")
            observed = payload.get("observed_unit") or payload.get("unit")
            allowed = set(_as_list(cond.get("quantity_kind_in"))) or {
                "Power",
                "Energy",
            }
            # Ratio / other non-power-energy kinds are out of scope for this rule
            if qk and qk not in allowed:
                return ValidationResult(
                    rule_name=rule.name,
                    passed=True,
                    severity=severity,
                    message="not applicable for quantity kind",
                    rule_type=rule.rule_type,
                    target_registry=rule.target_registry,
                    details={"quantity_kind": qk},
                )
            if unit_status == "incompatible":
                return ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    severity=severity,
                    message=rule.description
                    or "Energy metric unit incompatible with quantity kind",
                    rule_type=rule.rule_type,
                    target_registry=rule.target_registry,
                    details={"quantity_kind": qk, "unit": observed},
                )
            if payload.get("domain") == "energy" and not qk and observed:
                return ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    severity=severity,
                    message=rule.description
                    or "Energy metric must distinguish power from energy (quantity kind)",
                    rule_type=rule.rule_type,
                    target_registry=rule.target_registry,
                )
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                severity=severity,
                rule_type=rule.rule_type,
                target_registry=rule.target_registry,
            )

        # default: pass if nothing to evaluate
        return ValidationResult(
            rule_name=rule.name,
            passed=True,
            severity=severity,
            rule_type=rule.rule_type,
            target_registry=rule.target_registry,
            details={"note": "no evaluable condition"},
        )

    def _to_entry(self, row) -> RuleEntry:
        return RuleEntry(
            name=row.name,
            description=row.description,
            rule_type=row.rule_type,
            target_registry=row.target_registry,
            condition=dict(row.condition or {}),
            severity=row.severity or "error",
            status=row.status or "active",
            id=row.id,
            review_status=row.review_status or "approved",
        )


def get_rule_registry_service(
    session: Optional[Session] = None,
) -> RuleRegistryService:
    return RuleRegistryService(session=session)
