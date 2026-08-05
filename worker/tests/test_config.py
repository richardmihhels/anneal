from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from worker.config import load_customers


def _customer() -> dict[str, object]:
    return {
        "organization_id": "org_acme",
        "agent_id": "support-v1",
        "repo": "acme/support",
        "config_path": "agent/prompts.py",
        "baseline_prompt": "Be helpful.",
        "seed_set": [
            {"context": "resolved", "label": "pass"},
            {"context": "correct tool", "label": "pass"},
            {"context": "hallucinated policy", "label": "fail"},
            {"context": "unresolved", "label": "fail"},
        ],
    }


def test_load_customers_from_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNEAL_CUSTOMERS_JSON", json.dumps([_customer()]))
    customers = load_customers()
    assert len(customers) == 1
    assert customers[0].organization_id == "org_acme"
    assert customers[0].seed_labels == ("pass", "pass", "fail", "fail")


def test_load_customers_requires_both_seed_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    customer = _customer()
    customer["seed_set"] = [{"context": f"pass {index}", "label": "pass"} for index in range(4)]
    monkeypatch.setenv("ANNEAL_CUSTOMERS_JSON", json.dumps(customer))
    with pytest.raises(ValidationError, match="both pass and fail"):
        load_customers()


def test_load_customers_rejects_unknown_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    customer = _customer()
    customer["unexpected"] = True
    monkeypatch.setenv("ANNEAL_CUSTOMERS_JSON", json.dumps(customer))
    with pytest.raises(ValidationError, match="unexpected"):
        load_customers()
