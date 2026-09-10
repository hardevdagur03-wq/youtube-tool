"""Token usage tracking and estimation."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


def estimate_input_tokens(
    transcript: str,
    system_prompt: str,
    user_prompt: str,
) -> int:
    return estimate_tokens(system_prompt) + estimate_tokens(user_prompt) + estimate_tokens(transcript)


def estimate_output_tokens(expected_output_words: int = 500) -> int:
    return expected_output_words * 2
