from enum import Enum

class Role(str, Enum):
    admin = "admin"
    seller = "seller"
    customer = "customer"
