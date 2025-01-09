from authlib.integrations.starlette_client import OAuth
from app.core.config import settings

oauth = OAuth()

# Google OAuth Configuration
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Facebook OAuth Configuration
oauth.register(
    name="facebook",
    client_id=settings.FACEBOOK_CLIENT_ID,
    client_secret=settings.FACEBOOK_CLIENT_SECRET,
    api_base_url="https://graph.facebook.com/",
    authorize_url="https://www.facebook.com/v12.0/dialog/oauth",
    access_token_url="https://graph.facebook.com/v12.0/oauth/access_token",
    client_kwargs={"scope": "email public_profile"},
)
