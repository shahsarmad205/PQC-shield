"""PQCService tests: KEM and signature round-trips. Audit log write mocked in conftest."""
import pytest

from app.services.pqc_service import KEM_ALGORITHMS, SIG_ALGORITHMS, oqs

# Signature algorithms we test; only those enabled in the loaded liboqs (avoids MechanismNotSupportedError).
_SIG_ALGS_TO_TEST = (
    [a for a in ("ML-DSA-65", "SPHINCS+-SHA2-128f-simple") if a in oqs.get_enabled_sig_mechanisms()]
    if oqs is not None
    else ["ML-DSA-65", "SPHINCS+-SHA2-128f-simple"]
)


@pytest.mark.parametrize("algorithm", ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"])
@pytest.mark.asyncio
async def test_kem_round_trip_shared_secrets_match(pqc_service, algorithm):
    """Keygen → encapsulate → decapsulate; shared secrets must match."""
    pub_b64, sec_b64 = await pqc_service.keygen(algorithm)
    assert pub_b64 and sec_b64

    ct_b64, ss_enc_b64 = await pqc_service.encapsulate(algorithm, pub_b64)
    assert ct_b64 and ss_enc_b64

    ss_dec_b64 = await pqc_service.decapsulate(algorithm, sec_b64, ct_b64)
    assert ss_dec_b64 == ss_enc_b64


@pytest.mark.parametrize("algorithm", _SIG_ALGS_TO_TEST)
@pytest.mark.asyncio
async def test_sign_verify_round_trip(pqc_service, algorithm):
    """Keygen → sign → verify returns True."""
    pub_b64, sec_b64 = await pqc_service.keygen(algorithm)
    assert pub_b64 and sec_b64

    message = b"test message for PQC signature"
    sig_b64 = await pqc_service.sign(algorithm, sec_b64, message)
    assert sig_b64

    ok = await pqc_service.verify(algorithm, pub_b64, message, sig_b64)
    assert ok is True


@pytest.mark.parametrize("algorithm", _SIG_ALGS_TO_TEST)
@pytest.mark.asyncio
async def test_sign_verify_rejects_tampered_message(pqc_service, algorithm):
    """Verify returns False when message is tampered."""
    pub_b64, sec_b64 = await pqc_service.keygen(algorithm)
    sig_b64 = await pqc_service.sign(algorithm, sec_b64, b"original")
    ok = await pqc_service.verify(algorithm, pub_b64, b"tampered", sig_b64)
    assert ok is False


def test_kem_algorithms_defined():
    assert "ML-KEM-512" in KEM_ALGORITHMS
    assert "ML-KEM-768" in KEM_ALGORITHMS
    assert "ML-KEM-1024" in KEM_ALGORITHMS


def test_sig_algorithms_include_required():
    assert "ML-DSA-65" in SIG_ALGORITHMS
    assert "SPHINCS+-SHA2-128f-simple" in SIG_ALGORITHMS
