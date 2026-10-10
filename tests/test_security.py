from scarascope.security.rate_limits import RequestLimiter
from scarascope.api.dependencies import require_api_key
from scarascope.core.config import Settings
from fastapi import HTTPException
import pytest


def test_rate_limiter_blocks_after_budget():
    limiter=RequestLimiter()
    assert limiter.allow("test",2)
    assert limiter.allow("test",2)
    assert not limiter.allow("test",2)
    assert limiter.allow("other",2)


def test_production_auth_flag_requires_configured_key():
    with pytest.raises(HTTPException) as error:
        require_api_key(x_api_key=None,settings=Settings(require_auth=True,app_api_key=""))
    assert error.value.status_code==503


def test_configured_api_key_enforced():
    with pytest.raises(HTTPException) as error:
        require_api_key(x_api_key="incorrect",settings=Settings(app_api_key="abc"))
    assert error.value.status_code==401
    require_api_key(x_api_key="abc",settings=Settings(app_api_key="abc"))
