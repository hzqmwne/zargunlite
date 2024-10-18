import os
import re
import sqlite3
from collections.abc import Collection, Iterable, Mapping, Sequence
from contextlib import closing
from typing import Any

from zargunlite.model import ZircoliteRule, ZircoliteRuleMatchResult


def sqlite_udf_regexp(x: str, y: str | None) -> int:
    if y is None:
        return 0
    if re.search(x, y):
        return 1
    else:
        return 0


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

    def _execute_sql(self, sql: str, params: Mapping[str, object] | Sequence[object] = ()) -> list[sqlite3.Row]:
        with closing(self._db_connection.cursor()) as cursor:
            r = cursor.execute(sql, params)
            return r.fetchall()

    def _create_table(self, field_defs: list[tuple[str, str]]) -> None:
        # FIXME: escape field
        fields_part = ", ".join(f"'{field}' {typ}" for field, typ in field_defs) + ", "
        stmt = f"CREATE TABLE logs ( row_id INTEGER, {fields_part} PRIMARY KEY(row_id AUTOINCREMENT) );"
        self._execute_sql(stmt)

    def _insert_data_row(self, d: Mapping[str, Any]) -> None:
        column_define_list = []
        value_define_list = []
        for k, v in d.items():
            # FIXME: escape
            column_define = f"'{k}'"
            value_define = "'{}'".format(str(v).replace("'", "''"))
            column_define_list.append(column_define)
            value_define_list.append(value_define)

        columns_define = ", ".join(column_define_list)
        values_define = ", ".join(value_define_list)
        insert_stmt = f"INSERT INTO logs ({columns_define}) VALUES ({values_define});"
        self._execute_sql(insert_stmt)

    def load_data(
        self,
        data: Collection[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
        *,
        fields: Collection[tuple[str, type]] | None = None,
    ) -> None:
        if not fields:
            assert isinstance(data, Collection)
            field_map: dict[str, type] = {}
            for d in data:  # assert data is Collection because we need extra iter on it to extract fields
                field_map.update({k: type(v) for k, v in d.items()})
        else:
            # here, data can be any iterable object
            field_map = {k: t for k, t in fields}

        field_name_lower_seens: set[str] = set()
        field_define_list: list[tuple[str, str]] = []
        for field_name, field_type in field_map.items():
            field_name_lower = field_name.lower()
            if field_name_lower in field_name_lower_seens:
                # sqlite is case insensitive, so must drop duplicate one
                continue
            field_name_lower_seens.add(field_name_lower)

            sql_type_define = "INTEGER" if issubclass(field_type, int) else "TEXT COLLATE NOCASE"
            # FIXME: escape
            field_define = (field_name, sql_type_define)
            field_define_list.append(field_define)
        self._create_table(field_define_list)

        for d in data:
            self._insert_data_row(d)

    def create_index(self, field: str) -> None:
        # FIXME: escape field
        self._execute_sql(f'CREATE INDEX "idx_{field}" ON "logs" ("{field}");')

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
