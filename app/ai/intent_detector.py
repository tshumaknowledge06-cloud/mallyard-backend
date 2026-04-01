def detect_intent(message: str) -> str:
    text = message.lower()

    tracking_keywords = [
        "track",
        "where is my order",
        "order status",
        "delivery status",
        "has my order arrived",
        "where is my delivery",
    ]

    if any(k in text for k in tracking_keywords):
        return "order_tracking"

    return "unknown"