from pydantic import BaseModel

class GroupCreateSchema(BaseModel):
    name: str
    owner_id: int

class GroupUpdateSchema(BaseModel):
    name: str | None = None
    owner_id: int | None = None

class GroupResponseSchema(BaseModel):
    id: int
    name: str
    owner_id: int

    class Config:
        from_attributes = True