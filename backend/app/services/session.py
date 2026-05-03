from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_serializer = URLSafeTimedSerializer(settings.session_secret_key)

# Toma el UUID del usuario y devuelve un string firmado criptográficamente con itsdangerous.
# Este string es el que se mete en la cookie.
def sign_session(user_id: str) -> str:
    return _serializer.dumps(user_id)


# Recibe el valor de la cookie, verifica la firma y que no haya caducado y devuelve el user_id original.
def verify_session(cookie_value: str) -> str:
    max_age = settings.session_max_age_days * 86400
    return _serializer.loads(cookie_value, max_age=max_age)


__all__ = ["BadSignature", "SignatureExpired", "sign_session", "verify_session"]

# La idea es que la cookie no contiene una contraseña ni un JWT, sino sino simplemente el user_id firmado.
# Si alguien la manipula, la firma falla y se rechaza.
