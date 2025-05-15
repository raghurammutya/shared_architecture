from pydantic import BaseModel, EmailStr, Field
from app.models.enums import UserRole

class UserCreateSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., regex=r"^\+\d{10,15}$")  # Validates phone numbers
    role: UserRole = UserRole.USER  # Default role


class UserUpdateSchema(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None
    phone_number: str | None

class UserResponseSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole

    class Config:
        orm_mode = True