import re
import math

def password_score(pwd):
    if not pwd:
        return 0.0
    n = len(pwd)
    charset_size = 0
    if re.search(r"[a-z]", pwd):
        charset_size += 26
    if re.search(r"[A-Z]", pwd):
        charset_size += 26
    if re.search(r"\d", pwd):
        charset_size += 10
    if re.search(r"[^a-zA-Z0-9]", pwd):
        charset_size += 33
    if charset_size == 0:
        return 0.0
    entropy = n * math.log2(charset_size)
    penalty = 0.0
    if len(set(pwd)) == 1:
        penalty += entropy * 0.8
    for i in range(len(pwd) - 2):
        if ord(pwd[i+1]) == ord(pwd[i]) + 1 and ord(pwd[i+2]) == ord(pwd[i]) + 2:
            penalty += 10
    common_patterns = ["123", "abc", "qwerty", "password", "admin", "letmein", "welcome", "monkey", "dragon", "master", "login", "princess"]
    pwd_lower = pwd.lower()
    for pattern in common_patterns:
        if pattern in pwd_lower:
            penalty += 20
    entropy = max(0, entropy - penalty)
    if entropy < 28:
        score = entropy / 28 * 0.2
    elif entropy < 35:
        score = 0.2 + (entropy - 28) / 7 * 0.2
    elif entropy < 60:
        score = 0.4 + (entropy - 35) / 25 * 0.3
    elif entropy < 80:
        score = 0.7 + (entropy - 60) / 20 * 0.2
    else:
        score = 0.9 + min(1, (entropy - 80) / 40) * 0.1
    return min(score, 1.0)