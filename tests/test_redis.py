import pytest
import asyncio
from chatbot_ai_system.database.redis import RedisClient

@pytest.fixture
async def redis_test_client():
    client = RedisClient()
    # Assuming redis is running in docker
    await client.connect("redis://localhost:6379/0")
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_redis_set_get(redis_test_client):
    test_key = "test_key"
    test_value = {"foo": "bar"}
    
    await redis_test_client.set(test_key, test_value)
    retrieved_value = await redis_test_client.get(test_key)
    
    assert retrieved_value == test_value
    
    await redis_test_client.delete(test_key)
    deleted_value = await redis_test_client.get(test_key)
    assert deleted_value is None

@pytest.mark.asyncio
async def test_redis_ttl(redis_test_client):
    test_key = "ttl_key"
    test_value = "ttl_value"
    
    await redis_test_client.set(test_key, test_value, ttl=1)
    
    val = await redis_test_client.get(test_key)
    assert val == test_value
    
    await asyncio.sleep(1.1)
    
    val_after = await redis_test_client.get(test_key)
    assert val_after is None
