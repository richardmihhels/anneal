"""Validated customer configuration loading for the weekly worker."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from worker.models import CustomerConfig


class SeedExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: str = Field(min_length=1)
    label: Literal["pass", "fail"]


class CustomerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    config_path: str = Field(min_length=1)
    baseline_prompt: str = Field(min_length=1)
    seed_set: list[SeedExample] = Field(min_length=4)
    baseline_skills: list[str] = Field(default_factory=list)
    base_branch: str = Field(default="main", min_length=1)

    @model_validator(mode="after")
    def seed_set_contains_both_labels(self) -> CustomerSettings:
        labels = {example.label for example in self.seed_set}
        if labels != {"pass", "fail"}:
            raise ValueError("seed_set must contain both pass and fail examples")
        return self

    def to_customer_config(self) -> CustomerConfig:
        return CustomerConfig(
            organization_id=self.organization_id,
            agent_id=self.agent_id,
            repo=self.repo,
            config_path=self.config_path,
            baseline_prompt=self.baseline_prompt,
            seed_contexts=tuple(example.context for example in self.seed_set),
            seed_labels=tuple(example.label for example in self.seed_set),
            baseline_skills=tuple(self.baseline_skills),
            base_branch=self.base_branch,
        )


def _raw_configuration() -> object:
    inline = os.environ.get("ANNEAL_CUSTOMERS_JSON", "").strip()
    if inline:
        return json.loads(inline)

    config_path = Path(os.environ.get("ANNEAL_CONFIG_PATH", "anneal.yml"))
    if not config_path.is_file():
        raise RuntimeError("No customer configuration found. Set ANNEAL_CUSTOMERS_JSON or ANNEAL_CONFIG_PATH.")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def load_customers() -> list[CustomerConfig]:
    raw = _raw_configuration()
    if isinstance(raw, dict) and "customers" in raw:
        raw = raw["customers"]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("Customer configuration must contain at least one customer")
    return [CustomerSettings.model_validate(item).to_customer_config() for item in raw]
