"""Alert rule CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.alert import AlertRule
from app.schemas.alert import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate

router = APIRouter()


@router.get("", response_model=list[AlertRuleRead])
async def list_alerts(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List alert rules for a given user. Auth is added in a later iteration."""
    result = await db.execute(select(AlertRule).where(AlertRule.user_id == user_id))
    return list(result.scalars().all())


@router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    user_id: UUID,
    payload: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    rule = AlertRule(user_id=user_id, **payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleRead)
async def update_alert(
    rule_id: UUID,
    payload: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")

    # Only persist fields the caller actually sent.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    await db.delete(rule)
    await db.commit()
