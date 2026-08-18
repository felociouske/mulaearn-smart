"""
Signature verification for BluePay's incoming webhooks.

Kept separate from client.py on purpose: client.py is OUTBOUND (we call
BluePay), this file is INBOUND (BluePay calls us) — different trust
boundary, worth being able to audit ("can someone fake a payment
confirmation to us") in isolation from the request-sending code.
"""
import hashlib
import hmac
import re

from django.conf import settings

_SIGNATURE_RE = re.compile(r"^v1=([a-f0-9]{64})$")


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    raw_body MUST be the exact, unparsed request bytes (request.body in
    the view, read BEFORE request.data is touched). BluePay signs the
    raw JSON on the wire, not a re-serialized version of it — if you
    json.loads() then json.dumps() the body before checking, whitespace
    or key-ordering differences will make a genuine webhook fail
    verification even though the data is identical.

    Returns False (never raises) for a missing/malformed header — the
    caller should treat that exactly like a bad signature, i.e. reject
    with 401, not 500.
    """
    if not signature_header:
        return False

    match = _SIGNATURE_RE.match(signature_header)
    if not match:
        return False

    expected = hmac.new(
        settings.BLUEPAY_API_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time compare — a timing side-channel here would let an
    # attacker recover the correct signature one byte at a time by
    # measuring response latency across many forged requests.
    return hmac.compare_digest(expected, match.group(1))