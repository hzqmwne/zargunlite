import dataclasses
from typing import Any


@dataclasses.dataclass(slots=True, kw_only=True)
class ZircoliteRule:
    title: str
    id: str = ""
    status: str = ""
    description: str = ""
    author: str = ""
    tags: list[str] = dataclasses.field(default_factory=list)
    falsepositives: list[str] = dataclasses.field(default_factory=list)
    level: str = ""
    rule: list[str]
    filename: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class ZircoliteRuleMatchResult:
    title: str
    id: str
    description: str
    sigmafile: str
    sigma: list[str]  # ZircoliteRule.rule
    rule_level: str
    tags: list[str]
    count: int
    matches: list[dict[str, Any]]


# ---


@dataclasses.dataclass(slots=True, kw_only=True)
class ZircoliteFieldMappingSplitConfig:
    separator: str
    equal: str


@dataclasses.dataclass(slots=True, kw_only=True)
class ZircoliteFieldMappingConfig:
    exclusions: list[str]
    useless: list[Any]
    mappings: dict[str, str]
    alias: dict[str, str]
    split: dict[str, ZircoliteFieldMappingSplitConfig]
