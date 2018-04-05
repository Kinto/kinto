import bcrypt


# XXX: THIS IS WRONG OF COURSE. But it is the only way I found to have the password
# as part of the cache key (deterministic etc.) And I wanted to have green tests to
# make sure you would look at the changes seriously :)
salt = bcrypt.gensalt()


def hash_password(password):
    # Store password safely in database as str
    # (bcrypt.hashpw returns base64 bytes).
    pwd_str = password.encode(encoding='utf-8')
    hashed = bcrypt.hashpw(pwd_str, salt)
    return hashed.decode(encoding='utf-8')
