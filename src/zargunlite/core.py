import os
import re
import sqlite3
import string
from collections.abc import Collection, Iterable, Mapping, Sequence
from contextlib import closing
from types import TracebackType
from typing import Any

from zargunlite.model import ZargunException, ZircoliteRule, ZircoliteRuleMatchResult


def sqlite_udf_regexp(x: str, y: object | None) -> int:
    if y is None:
        return 0
    if re.search(x, str(y)):
        return 1
    else:
        return 0


def strict_field_name_check(field_name: str) -> bool:
    return all(c in string.ascii_letters + string.digits + "_" for c in field_name)


def repr_to_sqlite_name_literal(s: str) -> str:
    # FIXME: escape more special chars
    return "`{}`".format(s.replace("`", "``"))


def repr_to_sqlite_value_literal(v: object) -> str:
    s = str(v)
    if isinstance(v, int):
        return s
    safe_chars = string.digits + string.ascii_letters + string.punctuation + " "
    if all(c in safe_chars for c in s):
        return "'{}'".format(s.replace("'", "''"))
    else:
        return f"X'{s.encode().hex()}'"


class ZargunCore:
    __slots__ = ("_db_location", "_db_connection", "_limit")

    def __init__(
        self,
        *,
        db_location: str | bytes | os.PathLike[str] | os.PathLike[bytes] = ":memory:",
        limit: int = -1,
    ) -> None:
        self._db_location = db_location
        self._db_connection = self._create_connection()
        self._limit = limit

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_location)
        conn.row_factory = sqlite3.Row
        conn.create_function("regexp", 2, sqlite_udf_regexp)
        return conn

    def close(self) -> None:
        self._db_connection.close()

    def __enter__(self) -> "ZargunCore":  # TODO: when increase python require to >=3.11, we can use typing.Self
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        _ = exc_type, exc_value
        self.close()

    def _execute_sql(self, sql: str, params: Mapping[str, object] | Sequence[object] = ()) -> list[sqlite3.Row]:
        with closing(self._db_connection.cursor()) as cursor:
            r = cursor.execute(sql, params)
            return r.fetchall()

    def _create_table(self, field_defs: list[tuple[str, str]]) -> None:
        fields_part = "".join(f"{repr_to_sqlite_name_literal(field)} {typ}, " for field, typ in field_defs)
        stmt = f"CREATE TABLE `logs` ( `row_id` INTEGER, {fields_part} PRIMARY KEY(row_id AUTOINCREMENT) );"
        self._execute_sql(stmt)

    def _insert_data_row(self, d: Mapping[str, Any]) -> None:
        column_define_list = []
        value_list = []
        for k, v in d.items():
            column_define = repr_to_sqlite_name_literal(k)
            column_define_list.append(column_define)
            value_list.append(v)

        columns_define = ", ".join(column_define_list)
        parameters_define = ", ".join("?" * len(value_list))
        if column_define_list:
            insert_stmt = f"INSERT INTO `logs` ({columns_define}) VALUES ({parameters_define});"
        else:
            insert_stmt = "INSERT INTO `logs` DEFAULT VALUES;"
        self._execute_sql(insert_stmt, value_list)

    def load_data(
        self,
        data: Collection[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
        *,
        fields: Collection[tuple[str, type]] | None = None,
        strict_field_name: bool = True,
    ) -> None:
        if not fields:
            assert isinstance(data, Collection)
            field_map: dict[str, type] = {}
            for d in data:  # assert data is Collection because we need extra iter on it to extract fields
                field_map.update({k: type(v) for k, v in d.items()})
        else:
            # here, data can be any iterable object
            field_map = {k: t for k, t in fields}

        if strict_field_name:
            for field_name in field_map.keys():
                if not strict_field_name_check(field_name):
                    raise ZargunException(f"strict field name check failed: {field_name!r}")

        field_name_lower_seens: set[str] = set()
        field_define_list: list[tuple[str, str]] = []
        for field_name, field_type in field_map.items():
            field_name_lower = field_name.lower()
            if field_name_lower in field_name_lower_seens:
                # sqlite is case insensitive, so must drop duplicate one
                continue
            field_name_lower_seens.add(field_name_lower)

            sql_type_define = "INTEGER" if issubclass(field_type, int) else "TEXT COLLATE NOCASE"
            field_define = (field_name, sql_type_define)
            field_define_list.append(field_define)
        self._create_table(field_define_list)

        for d in data:
            self._insert_data_row(d)

    def create_index(self, field: str) -> None:
        sql = "CREATE INDEX {} ON `logs` ({});".format(
            repr_to_sqlite_name_literal(f"idx_{field}"),
            repr_to_sqlite_name_literal(field),
        )
        self._execute_sql(sql)

    def execute_sqlite_query(self, sql: str) -> list[dict[str, Any]]:
        r = []
        try:
            rows = self._execute_sql(sql)
            r = [{k: v for k, v in zip(row.keys(), row) if v is not None} for row in rows]
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):  # sqlite3.OperationalError: no such column: <>
                pass
            else:
                raise
        return r

    def execute_zircolite_rule(self, rule: ZircoliteRule) -> ZircoliteRuleMatchResult:
        all_count = 0
        all_matches = []
        for sql in rule.rule:
            matches = self.execute_sqlite_query(sql)
            count = len(matches)
            if count > 0 and (self._limit < 0 or count <= self._limit):
                all_count += count
                all_matches.extend(matches)
        r = ZircoliteRuleMatchResult(
            title=rule.title,
            id=rule.id,
            description=rule.description,
            sigmafile=rule.filename,
            sigma=list(rule.rule),
            rule_level=rule.level,
            tags=list(rule.tags),
            count=all_count,
            matches=all_matches,
        )
        return r
