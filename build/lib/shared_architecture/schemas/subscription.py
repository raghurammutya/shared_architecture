from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class SubscriptionType(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    STRATEGY_SPECIFIC = "strategy_specific"

class SubscriptionBase(BaseModel):
    user_id: int
    asset_id: int
    start_date: datetime
    end_date: datetime
    subscription_type: SubscriptionType
    tier_id: Optional[int] = None
    trial_end_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    current_usage: int = 0
    is_family_subscription: bool = False
    permissions: Optional[str] = None

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(SubscriptionBase):
    pass

class Subscription(SubscriptionBase):
    id: int

    class Config:
        from_attributes = True