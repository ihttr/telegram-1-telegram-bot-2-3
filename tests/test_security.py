import pytest
from app.services.security import validate_public_url, UnsafeUrl
@pytest.mark.asyncio
async def test_blocks_localhost():
    with pytest.raises(UnsafeUrl): await validate_public_url("http://localhost/admin")
