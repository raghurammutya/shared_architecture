# tests/test_timescaledb_mock.py

from shared_architecture.utils import connection_manager
from shared_architecture.models.symbol import Symbol

def test_symbol_query_positive():
    session = connection_manager.get_timescaledb_session()
    mock_symbol = Symbol(id=1, name="NIFTY", exchange="NSE", instrument_type="EQ")
    session.query.return_value.filter_by.return_value.all.return_value = [mock_symbol]

    results = session.query(Symbol).filter_by(exchange="NSE").all()
    assert len(results) == 1
    assert results[0].name == "NIFTY"

def test_symbol_query_negative():
    session = connection_manager.get_timescaledb_session()
    session.query.return_value.filter_by.return_value.all.return_value = []

    results = session.query(Symbol).filter_by(exchange="BSE").all()
    assert results == []