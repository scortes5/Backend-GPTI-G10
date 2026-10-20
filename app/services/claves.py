"""Hash de contraseñas con scrypt (biblioteca estándar): nunca se guarda la clave en texto plano."""
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1


def hashear(clave: str) -> str:
    sal = secrets.token_bytes(16)
    return f"scrypt${sal.hex()}${_derivar(clave, sal).hex()}"


def verificar(clave: str, clave_hash: str) -> bool:
    try:
        algoritmo, sal, esperado = clave_hash.split("$")
    except ValueError:
        return False
    if algoritmo != "scrypt":
        return False
    return hmac.compare_digest(_derivar(clave, bytes.fromhex(sal)).hex(), esperado)


def _derivar(clave: str, sal: bytes) -> bytes:
    return hashlib.scrypt(clave.encode(), salt=sal, n=_N, r=_R, p=_P)


# Hash de una clave aleatoria: se verifica contra él cuando el correo no existe, para que la
# respuesta tarde lo mismo y no revele qué correos están registrados.
HASH_SENUELO = hashear(secrets.token_urlsafe(16))
