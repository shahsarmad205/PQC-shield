"""Crypto API: KEM keygen and encapsulate (PQC)."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.cbom import User
from app.services.pqc_service import KEM_ALGORITHMS, PQCService

router = APIRouter()


@router.post("/kem/keygen")
async def kem_keygen(
    body: dict,
    _: User = Depends(get_current_user),
) -> dict:
    """Generate KEM key pair. Body: { \"algorithm\": \"ML-KEM-512\" | \"ML-KEM-768\" | \"ML-KEM-1024\" }."""
    algorithm = body.get("algorithm")
    if not algorithm or algorithm not in KEM_ALGORITHMS:
        raise HTTPException(
            400,
            detail=f"algorithm must be one of: {sorted(KEM_ALGORITHMS)}",
        )
    try:
        svc = PQCService()
        public_key_b64, secret_key_b64 = await svc.keygen(algorithm)
        return {"public_key": public_key_b64, "secret_key": secret_key_b64}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e))


@router.post("/kem/encapsulate")
async def kem_encapsulate(
    body: dict,
    _: User = Depends(get_current_user),
) -> dict:
    """Encapsulate secret with public key. Body: { \"algorithm\": \"...\", \"public_key\": \"<base64>\" }."""
    algorithm = body.get("algorithm")
    public_key = body.get("public_key")
    if not algorithm or algorithm not in KEM_ALGORITHMS:
        raise HTTPException(
            400,
            detail=f"algorithm must be one of: {sorted(KEM_ALGORITHMS)}",
        )
    if not public_key or not isinstance(public_key, str):
        raise HTTPException(400, detail="public_key (base64 string) is required")
    try:
        svc = PQCService()
        ciphertext_b64, shared_secret_b64 = await svc.encapsulate(
            algorithm, public_key.strip()
        )
        return {"ciphertext": ciphertext_b64, "shared_secret": shared_secret_b64}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e))
