from pydantic import BaseModel


class DeliveryMatchCreate(BaseModel):
    delivery_request_id: int
    delivery_partner_id: int


class DeliveryMatchOut(BaseModel):
    id: int
    delivery_request_id: int
    delivery_partner_id: int

    class Config:
        from_attributes = True
