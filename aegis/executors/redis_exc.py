# aegis/executors/redis.py
# I know. I hate it too. But otherwise the import would conflict with the file name.
"""
Provides a client for executing Redis-based operations for long-term memory.
"""
from typing import Optional
from urllib.parse import urlparse

from aegis.exceptions import ToolExecutionError
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    # Import the Redis client with an alias to avoid name conflicts.
    from redis.client import Redis as RedisClient

    REDIS_AVAILABLE = True
except ImportError:
    # If the library isn't installed, set the alias to None.
    RedisClient = None
    REDIS_AVAILABLE = False


class RedisExecutor:
    """A client for managing and executing Redis commands for agent memory."""

    def __init__(self):
        if not REDIS_AVAILABLE or RedisClient is None:
            raise ToolExecutionError("The 'redis' library is not installed.")

        self.client: Optional[RedisClient] = None
        try:
            config = get_config()
            redis_url = config.get("services", {}).get("redis_url")
            if not redis_url:
                raise ConnectionError(
                    "Redis URL not found in config.yaml under services.redis_url"
                )

            # Parse the URL to create a more compatible connection
            parsed_url = urlparse(redis_url)
            db_num = 0
            if parsed_url.path and parsed_url.path[1:].isdigit():
                db_num = int(parsed_url.path[1:])

            self.client = RedisClient(
                host=parsed_url.hostname,
                port=parsed_url.port,
                db=db_num,
                password=parsed_url.password,
                decode_responses=True,  # Makes the client return strings instead of bytes
            )
            if self.client is not None:
                self.client.ping()
                logger.info(
                    f"Connected to Redis at {parsed_url.hostname}:{parsed_url.port}"
                )
            else:
                logger.error("Failed to initialize Redis client.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # The client remains None, methods will fail gracefully.
            self.client = None

    def set_value(self, key: str, value: str) -> str:
        """Sets a string value for a given key in Redis."""
        if not self.client:
            raise ToolExecutionError(
                "Redis client is not connected. Check config and BEND service status."
            )
        try:
            self.client.set(key, value)
            logger.info(f"Successfully set memory key '{key}'.")
            return f"Value successfully set for key '{key}'."
        except Exception as e:
            logger.exception(f"Failed to set value for key '{key}' in Redis.")
            raise ToolExecutionError(f"Redis SET command failed: {e}")

    def get_value(self, key: str) -> str:
        """Gets a string value for a given key from Redis."""
        if not self.client:
            raise ToolExecutionError(
                "Redis client is not connected. Check config and BEND service status."
            )
        try:
            value = self.client.get(key)
            if value is None:
                logger.warning(f"No value found in memory for key '{key}'.")
                return f"No value found for key '{key}'."
            logger.info(f"Successfully retrieved memory for key '{key}'.")
            return value
        except Exception as e:
            logger.exception(f"Failed to get value for key '{key}' from Redis.")
            raise ToolExecutionError(f"Redis GET command failed: {e}")
