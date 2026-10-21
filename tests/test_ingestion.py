import csv

import pytest
import requests

from marketpulse.ingestion import fetch_market_data as ingestion


class FakeResponse:
    def __init__(self, text, content_type="text/csv"):
        self.text = text
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        pass

    def json(self):
        import json
        return json.loads(self.text)


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.called = False

    def get(self, url, params, timeout):
        self.called = True
        assert url == ingestion.API_URL
        assert params["function"] == "TIME_SERIES_DAILY"
        assert params["datatype"] == "csv"
        assert params["apikey"] == "dummy-key"
        assert timeout == 30
        return self.response


def test_fetch_symbol_saves_valid_csv(tmp_path, monkeypatch):
    csv_text = (
        "timestamp,open,high,low,close,volume\n"
        "2026-01-02,100,110,95,105,1000\n"
    )
    session = FakeSession(FakeResponse(csv_text))
    monkeypatch.setattr(ingestion, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(ingestion, "PROJECT_ROOT", tmp_path)

    output = ingestion.fetch_symbol(session, "AAPL", "dummy-key")

    assert session.called
    assert output == tmp_path / "raw" / "aapl_daily.csv"
    assert output.read_text(encoding="utf-8") == csv_text
    assert len(list(csv.DictReader(output.open(encoding="utf-8")))) == 1


def test_fetch_symbol_rejects_json_response(tmp_path, monkeypatch):
    response = FakeResponse(
        '{"Note": "API call frequency limit reached"}',
        content_type="application/json",
    )
    session = FakeSession(response)
    monkeypatch.setattr(ingestion, "RAW_DIR", tmp_path / "raw")

    with pytest.raises(RuntimeError, match="tidak mengembalikan CSV"):
        ingestion.fetch_symbol(session, "AAPL", "dummy-key")

    assert not (tmp_path / "raw").exists()


def test_fetch_symbol_rejects_invalid_csv(tmp_path, monkeypatch):
    response = FakeResponse(
        "timestamp,open,close\n2026-01-02,100,105\n"
    )
    session = FakeSession(response)
    monkeypatch.setattr(ingestion, "RAW_DIR", tmp_path / "raw")

    with pytest.raises(ValueError, match="Struktur CSV"):
        ingestion.fetch_symbol(session, "AAPL", "dummy-key")

    assert not (tmp_path / "raw").exists()


def test_fetch_symbol_propagates_http_error():
    class ErrorSession:
        def get(self, *args, **kwargs):
            response = requests.Response()
            response.status_code = 429
            raise requests.HTTPError("HTTP 429")

    with pytest.raises(requests.HTTPError, match="429"):
        ingestion.fetch_symbol(ErrorSession(), "AAPL", "dummy-key")
