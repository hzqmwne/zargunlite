from collections.abc import Generator
from typing import Any

import pytest

from zargunlite.core import ZargunCore
from zargunlite.model import ZargunException


@pytest.fixture
def zargun_core_instance() -> Generator[ZargunCore, None, None]:
    with ZargunCore() as instance:
        yield instance


class TestCoreDataAmount:
    @staticmethod
    def test_zero_count_data(zargun_core_instance: ZargunCore) -> None:
        zargun_core_instance.load_data([])
        r = zargun_core_instance.execute_sqlite_query("SELECT * FROM logs")
        assert r == []

    @staticmethod
    def test_lots_of_data(zargun_core_instance: ZargunCore) -> None:
        data = []
        for i in range(1, 1024):
            data.append({"a": i, "b": str(i)})
        zargun_core_instance.load_data(data)
        r = zargun_core_instance.execute_sqlite_query("SELECT * FROM logs WHERE a = 123")
        assert r == [{"row_id": 123, "a": 123, "b": "123"}]

    @staticmethod
    def test_zero_count_fields(zargun_core_instance: ZargunCore) -> None:
        zargun_core_instance.load_data([{}])
        r = zargun_core_instance.execute_sqlite_query("SELECT * FROM logs")
        assert r == [{"row_id": 1}]

    @staticmethod
    def test_lots_of_fields(zargun_core_instance: ZargunCore) -> None:
        d1 = {f"a{i}": i for i in range(1, 1000)}
        d2 = {f"b{i}": i for i in range(1, 1000)}
        data = [d1, d2]
        zargun_core_instance.load_data(data)
        r = zargun_core_instance.execute_sqlite_query("SELECT * FROM logs WHERE a456 = 456")
        assert len(r) == 1


class TestCoreDataSpecialChar:
    @staticmethod
    def test_valid_field_name_in_strict_mode(zargun_core_instance: ZargunCore) -> None:
        d = {"a": 1, "B": 2, "_": 3, "4": 40, "SELECT": "s"}
        data = [d]
        zargun_core_instance.load_data(data, strict_field_name=True)
        sql = "SELECT * FROM logs WHERE a = 1 AND b = 2 AND _ = 3 AND `4` = 40 AND `select` = 's'"
        r = zargun_core_instance.execute_sqlite_query(sql)
        assert r == [{"row_id": 1, "a": 1, "B": 2, "_": 3, "4": 40, "SELECT": "s"}]

    @staticmethod
    @pytest.mark.parametrize("data", [[{"\x00": 1}], [{"a&b": 1}], [{"c d": 1}]])
    def test_invalid_field_name_in_strict_mode(zargun_core_instance: ZargunCore, data: list[dict[str, Any]]) -> None:
        with pytest.raises(ZargunException):
            zargun_core_instance.load_data(data, strict_field_name=True)

    @staticmethod
    def test_special_name_char_in_non_strict_mode(zargun_core_instance: ZargunCore) -> None:
        d = {"a&b": 11, "c d": 22, "e'`f": 33, "\x01": 44}
        data = [d]
        zargun_core_instance.load_data(data, strict_field_name=False)
        r = zargun_core_instance.execute_sqlite_query("SELECT * FROM logs")
        assert r == [{"row_id": 1, "a&b": 11, "c d": 22, "e'`f": 33, "\x01": 44}]

    @staticmethod
    def test_special_value_char(zargun_core_instance: ZargunCore) -> None:
        utf8str = b"\xF0\x9F\x98\x83".decode()
        d = {"a": "a\0bc", "b": "de'f||g''h", "c": "i j`k``l", "d": "\xFF\xFE", "f": utf8str}
        data = [d]
        zargun_core_instance.load_data(data, strict_field_name=False)
        r = zargun_core_instance.execute_sqlite_query(f"SELECT * FROM logs WHERE f='{utf8str}'")
        assert r == [{"row_id": 1, "a": "a\0bc", "b": "de'f||g''h", "c": "i j`k``l", "d": "\xFF\xFE", "f": utf8str}]
