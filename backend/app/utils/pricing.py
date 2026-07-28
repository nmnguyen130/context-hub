MODEL_PRICING: dict[str, tuple[float, float]] = {
    # model_name: (input_cost_per_1m_tokens, output_cost_per_1m_tokens)
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def calculate_model_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate USD cost for a given model and prompt/completion token counts."""
    pricing = next(
        (rates for key, rates in MODEL_PRICING.items() if key in model_name),
        MODEL_PRICING["gemini-1.5-flash"],
    )
    input_rate, output_rate = pricing
    input_cost = (prompt_tokens / 1_000_000) * input_rate
    output_cost = (completion_tokens / 1_000_000) * output_rate
    return round(input_cost + output_cost, 8)
