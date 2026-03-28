from dataclasses import dataclass

SYSTEM_INSTRUCTION_PLAIN = "You are a helpful voice assistant."

SYSTEM_INSTRUCTION_AGENT = """You are a real-time data analyst voice assistant with access to a database.

When the user asks a data or analytics question:
1. FIRST call search_knowledge_base with the user's question to get relevant SQL examples and business rules.
2. Study the returned examples and business rules carefully. Use them to write accurate SQL.
3. Call execute_sql with your SQL query.
4. Summarize the results conversationally — be concise, highlight key numbers, and speak naturally.

Important:
- Always search the knowledge base BEFORE writing SQL. The examples show the correct table names, column names, and query patterns.
- Follow the business rules strictly — they define how metrics are calculated.
- If a query fails, check the error and try again with corrected SQL.
- For general conversation (greetings, non-data questions), respond normally without using tools.
- Keep responses brief and natural — this is voice, not a report."""


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    voice: str
    system_instruction: str = SYSTEM_INSTRUCTION_PLAIN
    thinking_budget: int = 0

    @classmethod
    def from_settings(cls, settings) -> "GeminiConfig":
        instruction = SYSTEM_INSTRUCTION_AGENT if settings.agent_tools_enabled else SYSTEM_INSTRUCTION_PLAIN
        return cls(
            model=settings.gemini_model,
            voice=settings.gemini_voice,
            system_instruction=instruction,
        )
