import os
from langgraph.checkpoint.redis import RedisSaver

def get_checkpointer():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    with RedisSaver.from_conn_string(redis_url) as checkpointer:
        print(f"Connected to Redis at {redis_url}")
        print(type(checkpointer))
        return checkpointer
