from collections.abc import Generator

import pytest

from zargunlite.core import ZargunCore
from zargunlite.model import ZircoliteRule, ZircoliteRuleMatchResult


@pytest.fixture
def zargun_core_instance() -> Generator[ZargunCore, None, None]:
    with ZargunCore() as instance:
        yield instance


@pytest.fixture
def zargun_core_instance_with_data(zargun_core_instance: ZargunCore) -> ZargunCore:
    data: list[dict[str, object]] = [
        {"category": "c1", "fieldA": "value1"},
        {"category": "c2", "fieldB": 22, "fieldD": 44},
        {"category": "c1", "fieldA": "value111", "fieldB": 222, "fieldC": "value333"},
        {"category": "c3", "fieldD": 44},
        {"category": "c4", "fieldD": 44},
        {"category": "c4", "fieldE": "000/abc/def/abc/ghi"},
        {"category": "c4", "fieldE": "111/abc/def/cba/ghi"},
        {"category": "c5", "fieldF": "JKL"},
        {"category": "c5", "fieldF": "jkl"},
    ]
    zargun_core_instance.load_data(data)
    zargun_core_instance.create_index("category")
    return zargun_core_instance


def test_core_sqlite_exception() -> None:
    with ZargunCore() as instance:
        instance.load_data([{"field": "value"}], fields=[("field", str)])
        with pytest.raises(Exception):
            instance.execute_sqlite_query("THIS IS AN INVALID SQL")


def test_core_sqlite_query_single(zargun_core_instance_with_data: ZargunCore) -> None:
    r = zargun_core_instance_with_data.execute_sqlite_query("SELECT * FROM logs WHERE fieldB = '22'")
    assert r == [{"row_id": 2, "category": "c2", "fieldB": 22, "fieldD": 44}]


def test_core_sqlite_query_single_nocase_string(zargun_core_instance_with_data: ZargunCore) -> None:
    r = zargun_core_instance_with_data.execute_sqlite_query("SELECT * FROM logs WHERE fieldF = 'Jkl'")
    assert r == [{"row_id": 8, "category": "c5", "fieldF": "JKL"}, {"row_id": 9, "category": "c5", "fieldF": "jkl"}]


def test_core_sqlite_query_like(zargun_core_instance_with_data: ZargunCore) -> None:
    r = zargun_core_instance_with_data.execute_sqlite_query("SELECT * FROM logs WHERE fieldA LIKE '%111'")
    assert r == [{"row_id": 3, "category": "c1", "fieldA": "value111", "fieldB": 222, "fieldC": "value333"}]


def test_core_sqlite_query_regex(zargun_core_instance_with_data: ZargunCore) -> None:
    query = r"SELECT * FROM logs WHERE fieldE REGEXP '\d+/([a-z]+)/def/\1/ghi'"
    r = zargun_core_instance_with_data.execute_sqlite_query(query)
    assert r == [{"row_id": 6, "category": "c4", "fieldE": "000/abc/def/abc/ghi"}]


def test_core_sqlite_query_no_such_column(zargun_core_instance_with_data: ZargunCore) -> None:
    r = zargun_core_instance_with_data.execute_sqlite_query("SELECT * FROM logs WHERE nosuchcolumn = ''")
    assert r == []


def test_core_zircolite_rule(zargun_core_instance_with_data: ZargunCore) -> None:
    rule = ZircoliteRule(
        title="Test",
        id="id",
        status="status",
        description="description",
        author="author",
        tags=["tag1"],
        falsepositives=[],
        level="level",
        rule=["SELECT * FROM logs WHERE (category='c2' OR category='c3') AND fieldD=44"],
        filename="filename",
    )
    r = zargun_core_instance_with_data.execute_zircolite_rule(rule)
    assert r == ZircoliteRuleMatchResult(
        title="Test",
        id="id",
        description="description",
        sigmafile="filename",
        sigma=["SELECT * FROM logs WHERE (category='c2' OR category='c3') AND fieldD=44"],
        rule_level="level",
        tags=["tag1"],
        count=2,
        matches=[
            {"row_id": 2, "category": "c2", "fieldB": 22, "fieldD": 44},
            {"row_id": 4, "category": "c3", "fieldD": 44},
        ],
    )
