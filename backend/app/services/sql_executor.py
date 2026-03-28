import httpx
from loguru import logger


class SQLExecutor:
    """Executes SQL queries against the mifix dashboard API."""

    def __init__(self, api_url: str, api_key: str, connection_id: str):
        self._api_url = api_url
        self._api_key = api_key
        self._connection_id = connection_id

    async def execute(self, sql: str) -> str:
        """Execute SQL and return results as formatted string."""
        logger.info(f"Executing SQL: {sql[:100]}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._api_url,
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "connection_id": self._connection_id,
                    "sql": sql,
                    "execution_source": "duckdb",
                },
            )

            # Capture full error body before raising
            if response.status_code >= 400:
                error_body = response.text
                logger.error(
                    f"SQL API error {response.status_code}: {error_body}"
                )
                return (
                    f"The query failed with error: {error_body}. "
                    "Please check the SQL and try again with corrected syntax."
                )

            data = response.json()

        # Format results for voice — keep it concise
        if isinstance(data, dict) and "data" in data:
            rows = data["data"]
            if not rows:
                return "The query ran successfully but returned no results."
            # Limit to 10 rows for voice readability
            preview = rows[:10]
            result = f"Query returned {len(rows)} rows. "
            for i, row in enumerate(preview, 1):
                result += f"Row {i}: {row}. "
            if len(rows) > 10:
                result += f"... and {len(rows) - 10} more rows."
            return result

        # Fallback: return raw response as string
        return str(data)[:2000]
