import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

JSONLiteralType: TypeAlias = str | int | float | bool | None
JSONType: TypeAlias = dict[str, "JSONType"] | list["JSONType"] | JSONLiteralType
JSONTypeRO: TypeAlias = Mapping[str, "JSONTypeRO"] | Sequence["JSONTypeRO"] | JSONLiteralType

# TODO: when increase python require to >=3.12, we can use the PEP 695 type alias syntax:
# type JSONLiteralType = str | int | float | bool | None
# type JSONType = dict[str, JSONType] | list[JSONType] | JSONLiteralType
# type JSONTypeRO = Mapping[str, "JSONTypeRO"] | Sequence["JSONTypeRO"] | JSONLiteralType


class ZargunException(Exception):
    pass


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
    exclusions: list[str] = dataclasses.field(default_factory=list)
    useless: list[Any] = dataclasses.field(default_factory=list)
    mappings: dict[str, str] = dataclasses.field(default_factory=dict)
    alias: dict[str, str] = dataclasses.field(default_factory=dict)
    split: dict[str, ZircoliteFieldMappingSplitConfig] = dataclasses.field(default_factory=dict)
