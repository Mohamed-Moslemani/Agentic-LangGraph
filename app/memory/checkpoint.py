import os
from langgraph.checkpoint.redis import RedisSaver

def get_checkpointer():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RedisSaver.from_conn_string(redis_url)
