from pydantic import BaseModel

class CartCheckoutRequest(BaseModel):
    delivery_method: str
    dropoff_address: str | None = None
    delivery_instructions: str | None = None
    customer_phone: str