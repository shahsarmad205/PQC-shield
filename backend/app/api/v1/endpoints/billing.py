"""Billing: usage, create checkout session (Stripe), create portal session (Stripe)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import get_current_org
from app.models.cbom import Organization, Plan, PLAN_QUOTAS

router = APIRouter()


class BillingUsageResponse(BaseModel):
    plan: str
    ops_used_this_month: int
    monthly_quota: int


class CreateCheckoutSessionBody(BaseModel):
    plan: str  # "starter" | "pro" | "enterprise"


class SessionUrlResponse(BaseModel):
    url: str


@router.get("", response_model=BillingUsageResponse)
async def get_billing_usage(
    org: Organization = Depends(get_current_org),
) -> BillingUsageResponse:
    """Return current plan and usage (ops used / quota) for the organization."""
    plan_value = org.plan.value if isinstance(org.plan, Plan) else str(org.plan)
    return BillingUsageResponse(
        plan=plan_value,
        ops_used_this_month=org.ops_used_this_month,
        monthly_quota=org.monthly_quota,
    )


def _get_stripe_price_id(plan: str) -> str | None:
    m = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "pro": settings.STRIPE_PRICE_PRO,
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
    }
    return (m.get(plan.lower()) or "").strip() or None


@router.post("/create-checkout-session", response_model=SessionUrlResponse)
async def create_checkout_session(
    body: CreateCheckoutSessionBody,
    org: Organization = Depends(get_current_org),
) -> SessionUrlResponse:
    """Create a Stripe Checkout Session for the given plan; returns URL to redirect the user."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )
    price_id = _get_stripe_price_id(body.plan)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unconfigured plan: {body.plan}",
        )

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base_url = (settings.FRONTEND_URL or "").rstrip("/")
    success_url = f"{base_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/billing"

    session_params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if org.stripe_customer_id:
        session_params["customer"] = org.stripe_customer_id
    else:
        session_params["metadata"] = {"organization_id": str(org.id)}

    session = stripe.checkout.Session.create(**session_params)
    url = session.url
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe did not return a checkout URL",
        )
    return SessionUrlResponse(url=url)


@router.post("/create-portal-session", response_model=SessionUrlResponse)
async def create_portal_session(
    org: Organization = Depends(get_current_org),
) -> SessionUrlResponse:
    """Create a Stripe Customer Portal session; returns URL to open for managing billing."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )
    if not org.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account linked. Subscribe to a plan first.",
        )

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base_url = (settings.FRONTEND_URL or "").rstrip("/")
    return_url = f"{base_url}/billing"

    session = stripe.billing_portal.Session.create(
        customer=org.stripe_customer_id,
        return_url=return_url,
    )
    url = session.url
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe did not return a portal URL",
        )
    return SessionUrlResponse(url=url)
