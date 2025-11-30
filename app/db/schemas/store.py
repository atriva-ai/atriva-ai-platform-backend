from pydantic import BaseModel

class StoreSchema(BaseModel):
    name: str

    class Config:
        from_attributes = True
        
class StoreResponse(BaseModel):
    name: str

