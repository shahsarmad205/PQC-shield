"""
PQCService — async wrappers around liboqs-python (KEM and signatures).
CPU-bound operations run in a thread pool via run_in_executor.
All keys and binary outputs are base64-encoded strings.
"""
import asyncio
import base64
import functools
from typing import Any

try:
    import oqs
except (ImportError, RuntimeError, OSError, SystemExit):
    oqs = None  # type: ignore[assignment]

KEM_ALGORITHMS = frozenset({"ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"})
SIG_ALGORITHMS = frozenset({
    "ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
    "SPHINCS+-SHA2-128f-simple",
})
SUPPORTED_ALGORITHMS = KEM_ALGORITHMS | SIG_ALGORITHMS


def _ensure_oqs() -> None:
    if oqs is None:
        raise RuntimeError(
            "liboqs-python is not installed. Install with: pip install liboqs-python"
        )


def _run_sync(sync_fn: Any, *args: Any, **kwargs: Any) -> Any:
    loop = asyncio.get_event_loop()
    if kwargs:
        return loop.run_in_executor(None, functools.partial(sync_fn, *args, **kwargs))
    return loop.run_in_executor(None, functools.partial(sync_fn, *args))


class PQCService:
    """Async PQC operations using liboqs-python. Keys and binary outputs are base64-encoded."""

    def __init__(self) -> None:
        _ensure_oqs()

    @staticmethod
    def _keygen_kem_sync(algorithm: str) -> tuple[str, str]:
        kem = oqs.KeyEncapsulation(algorithm)
        keypair_fn = getattr(kem, "generate_keypair", None) or getattr(kem, "keypair", None)
        if not keypair_fn:
            raise RuntimeError(f"KeyEncapsulation({algorithm}) has no keypair method")
        public_key = keypair_fn()
        secret_key = kem.export_secret_key()
        return (
            base64.standard_b64encode(public_key).decode("ascii"),
            base64.standard_b64encode(secret_key).decode("ascii"),
        )

    @staticmethod
    def _keygen_sig_sync(algorithm: str) -> tuple[str, str]:
        sig = oqs.Signature(algorithm)
        keypair_fn = getattr(sig, "generate_keypair", None) or getattr(sig, "keypair", None)
        if not keypair_fn:
            raise RuntimeError(f"Signature({algorithm}) has no keypair method")
        public_key = keypair_fn()
        secret_key = sig.export_secret_key()
        return (
            base64.standard_b64encode(public_key).decode("ascii"),
            base64.standard_b64encode(secret_key).decode("ascii"),
        )

    async def keygen(self, algorithm: str) -> tuple[str, str]:
        """Generate a key pair. Returns (public_key_b64, secret_key_b64)."""
        _ensure_oqs()
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm: {algorithm}. Supported: {sorted(SUPPORTED_ALGORITHMS)}"
            )
        if algorithm in KEM_ALGORITHMS:
            return await _run_sync(self._keygen_kem_sync, algorithm)
        return await _run_sync(self._keygen_sig_sync, algorithm)

    @staticmethod
    def _encapsulate_sync(algorithm: str, public_key_b64: str) -> tuple[str, str]:
        public_key = base64.standard_b64decode(public_key_b64)
        kem = oqs.KeyEncapsulation(algorithm)
        encap_fn = getattr(kem, "encap_secret", None) or getattr(kem, "encapsulate", None)
        if not encap_fn:
            raise RuntimeError(f"KeyEncapsulation({algorithm}) has no encap method")
        ciphertext, shared_secret = encap_fn(public_key)
        return (
            base64.standard_b64encode(ciphertext).decode("ascii"),
            base64.standard_b64encode(shared_secret).decode("ascii"),
        )

    async def encapsulate(
        self, algorithm: str, public_key_b64: str
    ) -> tuple[str, str]:
        """Encapsulate: returns (ciphertext_b64, shared_secret_b64)."""
        _ensure_oqs()
        if algorithm not in KEM_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} is not a KEM. Use one of: {sorted(KEM_ALGORITHMS)}")
        return await _run_sync(self._encapsulate_sync, algorithm, public_key_b64)

    @staticmethod
    def _decapsulate_sync(
        algorithm: str, secret_key_b64: str, ciphertext_b64: str
    ) -> str:
        secret_key = base64.standard_b64decode(secret_key_b64)
        ciphertext = base64.standard_b64decode(ciphertext_b64)
        kem = oqs.KeyEncapsulation(algorithm, secret_key=secret_key)
        decap_fn = getattr(kem, "decap_secret", None) or getattr(kem, "decapsulate", None)
        if not decap_fn:
            raise RuntimeError(f"KeyEncapsulation({algorithm}) has no decap method")
        shared_secret = decap_fn(ciphertext)
        return base64.standard_b64encode(shared_secret).decode("ascii")

    async def decapsulate(
        self,
        algorithm: str,
        secret_key_b64: str,
        ciphertext_b64: str,
    ) -> str:
        """Decapsulate: returns shared_secret_b64."""
        _ensure_oqs()
        if algorithm not in KEM_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} is not a KEM. Use one of: {sorted(KEM_ALGORITHMS)}")
        return await _run_sync(
            self._decapsulate_sync, algorithm, secret_key_b64, ciphertext_b64
        )

    @staticmethod
    def _sign_sync(algorithm: str, secret_key_b64: str, message: bytes) -> str:
        secret_key = base64.standard_b64decode(secret_key_b64)
        sig = oqs.Signature(algorithm, secret_key=secret_key)
        signature = sig.sign(message)
        return base64.standard_b64encode(signature).decode("ascii")

    async def sign(
        self,
        algorithm: str,
        secret_key_b64: str,
        message: bytes | str,
    ) -> str:
        """Sign a message. Returns signature_b64. Message can be bytes or str (UTF-8)."""
        _ensure_oqs()
        if algorithm not in SIG_ALGORITHMS:
            raise ValueError(
                f"Algorithm {algorithm} is not a signature scheme. Use one of: {sorted(SIG_ALGORITHMS)}"
            )
        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        return await _run_sync(self._sign_sync, algorithm, secret_key_b64, msg_bytes)

    @staticmethod
    def _verify_sync(
        algorithm: str,
        public_key_b64: str,
        message: bytes,
        signature_b64: str,
    ) -> bool:
        public_key = base64.standard_b64decode(public_key_b64)
        signature = base64.standard_b64decode(signature_b64)
        sig = oqs.Signature(algorithm)
        return sig.verify(message, signature, public_key)

    async def verify(
        self,
        algorithm: str,
        public_key_b64: str,
        message: bytes | str,
        signature_b64: str,
    ) -> bool:
        """Verify a signature. Message can be bytes or str (UTF-8). Returns True if valid."""
        _ensure_oqs()
        if algorithm not in SIG_ALGORITHMS:
            raise ValueError(
                f"Algorithm {algorithm} is not a signature scheme. Use one of: {sorted(SIG_ALGORITHMS)}"
            )
        msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
        return await _run_sync(
            self._verify_sync,
            algorithm,
            public_key_b64,
            msg_bytes,
            signature_b64,
        )
