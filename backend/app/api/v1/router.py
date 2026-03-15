"""API v1 router — includes all endpoint modules."""
from fastapi import APIRouter

from app.api.v1.endpoints import audit as audit_endpoints
from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.endpoints import billing as billing_endpoints
from app.api.v1.endpoints import cbom as cbom_endpoints
from app.api.v1.endpoints import compliance as compliance_endpoints
from app.api.v1.endpoints import crypto as crypto_endpoints
from app.api.v1.endpoints import keys as keys_endpoints

router = APIRouter(prefix="/api/v1")
router.include_router(audit_endpoints.router, prefix="/audit", tags=["audit"])
router.include_router(auth_endpoints.router, prefix="/auth", tags=["auth"])
router.include_router(billing_endpoints.router, prefix="/billing", tags=["billing"])
router.include_router(cbom_endpoints.router, prefix="/cbom", tags=["cbom"])
router.include_router(compliance_endpoints.router, prefix="/compliance", tags=["compliance"])
router.include_router(crypto_endpoints.router, prefix="/crypto", tags=["crypto"])
router.include_router(keys_endpoints.router, prefix="/keys", tags=["keys"])
