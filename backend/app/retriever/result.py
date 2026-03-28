from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalResult:
    """Result returned by a retriever strategy."""

    context: str
    confidence: float
    is_low_confidence: bool
    sources: list[str] = field(default_factory=list)
