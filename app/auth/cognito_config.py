import os

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET", "")
DOMAIN = os.getenv("COGNITO_DOMAIN", "")

REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI", "http://localhost:8000/auth/callback")
LOGOUT_REDIRECT_URI = os.getenv("COGNITO_LOGOUT_REDIRECT_URI", "http://localhost:8000/")

STATE_SECRET = os.getenv("STATE_SECRET", "CHANGE_ME")

ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
AUTH_URL = f"https://{DOMAIN}/oauth2/authorize"
TOKEN_URL = f"https://{DOMAIN}/oauth2/token"
LOGOUT_URL = f"https://{DOMAIN}/logout"



