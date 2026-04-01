ORDER_TRANSITIONS = {
    "pending": ["accepted", "rejected"],
    "accepted": ["preparing"],
    "preparing": ["packaged"],
    "packaged": ["awaiting_delivery_choice"],
    "awaiting_delivery_choice": ["delivery_requested", "completed"],
    "delivery_requested": ["delivery_assigned"],
    "delivery_assigned": ["out_for_delivery"],
    "out_for_delivery": ["completed"],
}

def validate_transition(current_status: str, new_status: str):
    allowed = ORDER_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise ValueError(f"Invalid transition from {current_status} to {new_status}")