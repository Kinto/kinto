import bcrypt


def hash_password(password):
    # Store password safely in database as str
    # (bcrypt.hashpw returns base64 bytes).
    pwd_str = password.encode(encoding='utf-8')
    hashed = bcrypt.hashpw(pwd_str, bcrypt.gensalt())
    return hashed.decode(encoding='utf-8')
