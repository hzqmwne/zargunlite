import time
from collections.abc import Mapping, Sequence

from zargunlite.default_config import DEFAULT_FIELD_MAPPING_CONFIG
from zargunlite.model import JSONLiteralType, JSONTypeRO, ZircoliteFieldMappingConfig


def flatten_json(x: JSONTypeRO) -> dict[tuple[str, ...], JSONLiteralType] | JSONLiteralType:
    value: dict[tuple[str, ...], JSONLiteralType] | JSONLiteralType | None = None
    if isinstance(x, Mapping):
        value = {}
        for k, v in x.items():
            r = flatten_json(v)
            if isinstance(r, Mapping):
                for sk, sv in r.items():
                    value[(k, *sk)] = sv
            else:
                value[(k,)] = r
    elif isinstance(x, Sequence):
        value = str(x)
    else:
        value = x
    return value


def mapping_field(
    y: dict[tuple[str, ...], JSONLiteralType],
    *,
    field_mapping_config: ZircoliteFieldMappingConfig = DEFAULT_FIELD_MAPPING_CONFIG,
) -> dict[str, JSONLiteralType]:
    result: dict[str, JSONLiteralType] = {}

    for ks, value in y.items():
        raw_key = ".".join(ks)

        # Applying exclusions. Be careful, the key/value pair is discarded if there is a partial match
        if any(exclusion in raw_key for exclusion in field_mapping_config.exclusions):
            continue

        # Excluding useless values (e.g. "null"). The value must be an exact match.
        if value in field_mapping_config.useless:
            continue

        # Applying field mappings
        if raw_key in field_mapping_config.mappings:
            key = field_mapping_config.mappings[raw_key]
        else:
            key = "".join(c for c in ks[-1] if c.isalnum())

        # Applying field splitting
        for tmp_key in {key, raw_key}:
            split_cfg = field_mapping_config.split.get(tmp_key)
            if not (split_cfg is not None and isinstance(value, str)):
                continue
            value_parts = value.split(split_cfg.separator)
            for value_part in value_parts:
                value_sub_parts = value_part.split(split_cfg.equal)
                if len(value_sub_parts) != 2:
                    continue
                k, v = value_sub_parts
                result[k] = result.get(k, v)

        # Applying key and aliases
        result[key] = result.get(key, value)
        for tmp_key in {key, raw_key}:
            alias = field_mapping_config.alias.get(tmp_key)
            if alias is not None:
                result[alias] = result.get(alias, value)

    return result


def filter_time_field(
    d: Mapping[str, JSONLiteralType],
    *,
    time_field: str = "SystemTime",
    time_after: time.struct_time | None = None,
    time_before: time.struct_time | None = None,
) -> bool:
    if (time_after is not None or time_before is not None) and isinstance(time_str_value := d.get(time_field), str):
        time_value = time.strptime(time_str_value.split(".", 1)[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        return (time_after is None or time_value > time_after) and (time_before is None or time_value < time_before)
    return True
