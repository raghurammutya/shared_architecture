from pydantic import BaseModel

class TradingAccountBaseSchema(BaseModel):
    broker_name: str
    api_key: str
    api_secret: str
    access_token: str | None = None
    account_alias: str | None = None

class TradingAccountCreateSchema(TradingAccountBaseSchema):
    pass

class TradingAccountUpdateSchema(BaseModel):
    access_token: str | None = None
    account_alias: str | None = None

class TradingAccountResponseSchema(TradingAccountBaseSchema):
    id: int
    user_id: int

    class Config:
        from_attributes = True
