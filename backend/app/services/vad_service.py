from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams


def create_vad_analyzer(
    confidence: float = 0.7,
    start_secs: float = 0.2,
    stop_secs: float = 0.2,
) -> SileroVADAnalyzer:
    """Factory function to create a configured SileroVADAnalyzer."""
    return SileroVADAnalyzer(
        params=VADParams(
            confidence=confidence,
            start_secs=start_secs,
            stop_secs=stop_secs,
        ),
    )
