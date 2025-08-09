from typing import Dict, Any
import time
from jwt import PyJWKClient, InvalidTokenError
import jwt  # PyJWT

from .cognito_config import JWKS_URL, ISSUER

_jwk_client = None
_last_fetch = 0
_cache_ttl = 60 * 10  # 10 minutes

def _get_jwk_client() -> PyJWKClient:
    global _jwk_client, _last_fetch
    now = time.time()
    if _jwk_client is None or (now - _last_fetch) > _cache_ttl:
        _jwk_client = PyJWKClient(JWKS_URL)
        _last_fetch = now
    return _jwk_client

def verify_jwt(token: str, audience: str) -> Dict[str, Any]:
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=ISSUER,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,   
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            },
            leeway=120,  # <-- allow 2 minutes clock skew
        )
        return claims
    except InvalidTokenError as e:
        raise
