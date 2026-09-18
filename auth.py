import base64, hashlib, hmac, secrets
PBKDF2_ROUNDS=240_000
def hash_password(password):
    if not isinstance(password,str) or len(password)<8:
        raise ValueError('Password must be at least 8 characters.')
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,PBKDF2_ROUNDS)
    return 'pbkdf2_sha256$%s$%s$%s' % (PBKDF2_ROUNDS,base64.b64encode(salt).decode(),base64.b64encode(digest).decode())
def verify_password(password, encoded):
    try:
        alg, rounds, salt_b64, digest_b64=encoded.split('$',3)
        if alg!='pbkdf2_sha256': return False
        salt=base64.b64decode(salt_b64); expected=base64.b64decode(digest_b64)
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,int(rounds))
        return hmac.compare_digest(actual,expected)
    except Exception:
        return False
