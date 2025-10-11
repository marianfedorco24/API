import re, ipaddress, validators, unicodedata
from urllib.parse import urlsplit, urlunsplit

ALLOWED = {"http", "https"}
URL_MAX_LEN = 2048

# scheme without colon, e.g., "https//example.com"
_MISSING_COLON_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*//')
def check_url(raw: str) -> str | None:
    """
    Normalize & validate a URL for DB storage.
    - Only http/https.
    - Adds https:// for bare domains and protocol-relative //host URLs.
    - Rejects credentials, fragments, malformed ports, missing-colon schemes.
    - Lowercases scheme/host; preserves path+query; strips fragment.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    # Fast-fail on "https//example.com" style typos (missing colon)
    if _MISSING_COLON_SCHEME.match(s):
        return None

    # Choose a safe base parse
    if s.startswith(("http://", "https://")):
        p = urlsplit(s)
    elif s.startswith("//"):                      # protocol-relative
        p = urlsplit("https:" + s)
    else:                                         # bare domain, etc.
        p = urlsplit("https://" + s)

    scheme = (p.scheme or "").lower()
    if scheme not in ALLOWED:
        return None

    # Must have a hostname
    host = p.hostname
    if not host:
        return None

    # Disallow credentials
    if p.username or p.password:
        return None

    # Validate/normalize port; p.port may raise ValueError if garbage
    try:
        port = p.port
    except ValueError:
        return None

    # Lowercase host
    host = host.lower()

    # Detect IPv6 to re-wrap with brackets
    is_ipv6 = False
    try:
        ip_obj = ipaddress.ip_address(host)
        is_ipv6 = ip_obj.version == 6
    except ValueError:
        # not an IP (fine — could be a domain)
        pass

    if is_ipv6:
        base = f"[{host}]"
    else:
        base = host

    netloc = f"{base}:{port}" if port else base

    normalized = urlunsplit((scheme, netloc, p.path or "", p.query or "", p.fragment or ""))

    # Length cap + conservative shape check
    if len(normalized) > URL_MAX_LEN:
        return None
    if not validators.url(normalized):
        return None

    return normalized

ALLOWED_SEPARATORS = set(" -_.")
NAME_MAX_LEN = 64
def normalize_name(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    s = unicodedata.normalize("NFC", raw).strip()
    if not s or len(s) > NAME_MAX_LEN:
        return None

    # reject control chars
    if any(ord(c) < 32 or ord(c) == 127 for c in s):
        return None

    # only letters (any script), digits, separators
    def ok(c: str) -> bool:
        if c in ALLOWED_SEPARATORS:
            return True
        cat = unicodedata.category(c)   # 'L*' = letters, 'N*' = numbers
        return cat[0] in ("L", "N")

    if not all(ok(c) for c in s):
        return None
    return s