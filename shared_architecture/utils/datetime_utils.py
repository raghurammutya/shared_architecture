from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import subscription as subscription_schema
from app.services import broker_service, symbol_service
from shared_architecture.db import get_db
import logging

router = APIRouter()


@router.post("/subscribe/", status_code=200)
async def subscribe_to_symbol(
    subscription: subscription_schema.SubscriptionCreate,
    db: Session = Depends(get_db),
    interval: str = '1second',
    get_market_depth: bool = False,
    get_exchange_quotes: bool = True
):
    """
    Endpoint to subscribe to a symbol for real-time feeds.
    """
    try:
        broker = await broker_service.get_broker_details(db)

        # Retrieve broker-specific token
        broker_token = await symbol_service.get_broker_token(
            db, subscription.instrument_key, broker.broker_name
        )

        # Check subscription limit
        if broker.subscription_limit is not None:
            # get count of current subscriptions.
            # replace with actual count query.
            count = 0
            if count >= broker.subscription_limit:
                raise HTTPException(
                    status_code=429, detail="Subscription limit exceeded"
                )

        await broker_service.subscribe_to_symbol(
            broker,
            subscription.instrument_key,
            broker_token,
            interval,
            get_market_depth,
            get_exchange_quotes,
        )
        return {"message": "Subscription successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error subscribing to symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe/", status_code=200)
async def unsubscribe_from_symbol(
    subscription: subscription_schema.SubscriptionCreate,
    db: Session = Depends(get_db),
    interval: str = '1second'
):
    """
    Endpoint to unsubscribe from a symbol.
    """
    try:
        broker = await broker_service.get_broker_details(db)

        # Retrieve broker-specific token
        broker_token = await symbol_service.get_broker_token(
            db, subscription.instrument_key, broker.broker_name
        )

        await broker_service.unsubscribe_from_symbol(
            broker, subscription.instrument_key, broker_token, interval
        )
        return {"message": "Unsubscription successful"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error unsubscribing from symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))