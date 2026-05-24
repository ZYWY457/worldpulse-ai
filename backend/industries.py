import os
from functools import lru_cache
from typing import Any

import yaml


INDUSTRY_IDS = {"overview", "trade", "finance", "tech", "supply_chain", "geopolitics", "content"}


@lru_cache(maxsize=1)
def load_industries() -> dict[str, dict[str, Any]]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "industries.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    industries = data.get("industries", {})
    return {key: value for key, value in industries.items() if key in INDUSTRY_IDS}


def get_industry(industry: str | None) -> dict[str, Any]:
    industries = load_industries()
    key = industry if industry in industries else "overview"
    return industries[key]


def get_industry_ids() -> list[str]:
    return list(load_industries().keys())
