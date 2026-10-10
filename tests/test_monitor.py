import pytest
from scarascope.services.monitor import scan_watches
from scarascope.storage.watchlist import add_watch
from scarascope.core.config import Settings

class FakeMonitor:
    def __init__(self):self.accession="0000000001-26-000001"
    async def latest(self,ticker):return self.accession,"8-K","2026-10-10"

@pytest.mark.asyncio
async def test_watchlist_baseline_then_change(tmp_path):
    settings=Settings(history_db_path=str(tmp_path/"state.sqlite3"))
    add_watch(settings.history_db_path,"MSFT")
    monitor=FakeMonitor()
    baseline=await scan_watches(settings,monitor)
    assert baseline.items[0].is_new_since_previous_check is False
    again=await scan_watches(settings,monitor)
    assert again.items[0].is_new_since_previous_check is False
    monitor.accession="0000000001-26-000002"
    changed=await scan_watches(settings,monitor)
    assert changed.items[0].is_new_since_previous_check is True
