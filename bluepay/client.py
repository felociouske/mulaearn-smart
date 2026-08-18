"""
BluePay (bluepay.co.ke) integration — Kenya M-Pesa STK push and status
polling.

Kept deliberately separate from payment/daraja.py: BluePay is a wrapper
gateway in front of Safaricom (not Daraja itself), with its own auth,
its own request/response shape, and its own webhook signing scheme.
Nothing in here talks to Safaricom directly — BluePay does that.

This module has NO dependency on any other app (activation, payment,
wallets) — it's a pure client for BluePay's REST API. The apps that use
it import initiate_stk_push()/check_payment_status() and decide what to
do with the result; this file doesn't know what an "ActivationSubmission"
or a "DepositRequest" is.

Required env vars (add to settings.py the same way DARAJA_* is wired —
see payment/daraja.py's docstring for that pattern):
  BLUEPAY_BASE_URL     Optional — defaults to "https://bluepay.co.ke".
  BLUEPAY_API_SECRET   Bearer token from BluePay dashboard -> API Keys.
                        Also the HMAC secret used to verify webhooks
                        (see bluepay/webhooks.py) — same key, two jobs.
  BLUEPAY_CHANNEL_ID   The channel_id (UUID) of your M-Pesa till/paybill,
                        from BluePay dashboard -> Payment channels.

One-time dashboard setup (not code): in the BluePay dashboard, under
Account -> Callback URL, set it to:
  https://<your-api-domain>/api/bluepay/callback/
BluePay POSTs every STK/B2C result there, signed. This is a SINGLE
webhook for the whole project — activation payments and deposit
payments both land on it. See bluepay/views.py for how it tells them
apart.
"""
import requests
from django.conf import settings

DEFAULT_BASE_URL = "https://bluepay.co.ke"


class BluepayError(Exception):
    """
    Raised for any non-success response from BluePay — callers should
    catch THIS, not requests.HTTPError or a raw KeyError, so a change in
    BluePay's error shape can't blow up as an unhandled 500 somewhere
    downstream.
    """

    def __init__(self, message, error_code=None, response_data=None):
        super().__init__(message)
        self.error_code = error_code
        self.response_data = response_data or {}


def _base_url():
    return getattr(settings, "BLUEPAY_BASE_URL", None) or DEFAULT_BASE_URL


def _headers():
    return {
        "Authorization": f"Bearer {settings.BLUEPAY_API_SECRET}",
        "Content-Type": "application/json",
    }


def _normalize_phone(phone_number):
    """
    BluePay normalizes MSISDNs itself, but we normalize first too so a
    malformed number fails fast with OUR error message instead of
    BluePay's generic INVALID_PHONE (422). Accepts the common Kenyan
    formats users might have stored: 0712345678, +254712345678,
    254712345678, 712345678.
    """
    digits = "".join(c for c in phone_number if c.isdigit())
    if digits.startswith("0"):
        return "254" + digits[1:]
    if digits.startswith("254"):
        return digits
    if len(digits) == 9:  # bare "712345678"
        return "254" + digits
    return digits


def _parse_json_response(resp):
    """Shared by both calls below — BluePay always answers with the same {"ok": bool, ...} envelope, even on errors."""
    try:
        data = resp.json()
    except ValueError:
        raise BluepayError(f"BluePay returned a non-JSON response ({resp.status_code}): {resp.text[:200]}")

    if not data.get("ok"):
        raise BluepayError(
            data.get("message") or data.get("error") or "BluePay request failed",
            error_code=data.get("error_code"),
            response_data=data,
        )
    return data


def initiate_stk_push(phone_number, amount, account_reference, callback_url=None):
    """
    Triggers an M-Pesa STK push via BluePay — the user gets a PIN prompt
    on their phone. Returns {"stk_request_id": int, "checkout_request_id": str}.

    account_reference is YOUR correlation id (max 64 chars, we truncate
    defensively). BluePay echoes it back verbatim in the webhook payload
    and in payment_status lookups — that's how bluepay/views.py routes a
    webhook back to the right ActivationSubmission or DepositRequest.
    Callers in this project always pass "ACT-<submission_id>" or
    "DEP-<deposit_id>" — see activation/views.py and payment/views.py.

    Raises BluepayError on any failure, including the 402
    INSUFFICIENT_PREPAID case (BluePay's own service-token balance is
    too low — a merchant-account problem, not the payer's) — callers
    should catch this and surface a friendly message rather than a 500.
    """
    payload = {
        "channel_id": settings.BLUEPAY_CHANNEL_ID,
        "phone": _normalize_phone(phone_number),
        "amount": int(amount),  # KES, whole numbers only — same constraint BluePay/Daraja both have
        "account_reference": str(account_reference)[:64],
    }
    if callback_url:
        payload["callback_url"] = callback_url

    try:
        resp = requests.post(
            f"{_base_url()}/api/stk_push.php",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as e:
        raise BluepayError(f"Could not reach BluePay: {e}")

    data = _parse_json_response(resp)
    return {
        "stk_request_id": data["stk_request_id"],
        "checkout_request_id": data["checkout_request_id"],
    }


def check_payment_status(checkout_request_id=None, account_reference=None):
    """
    Polls BluePay for the current state of an STK request. Use this as
    the backup path — BluePay's own docs say "No automatic webhook
    retries — use payment status as backup" — e.g. from a periodic
    Celery task for any ActivationSubmission/DepositRequest still
    PENDING a minute or two after the push was sent, in case the
    webhook never arrived.

    Pass exactly one of checkout_request_id (preferred — unambiguous)
    or account_reference. Returns the raw BluePay response dict; check
    result["paid"] (bool) rather than interpreting stk_status yourself,
    since BluePay's docs mark "paid" as the authoritative field.
    """
    if not checkout_request_id and not account_reference:
        raise ValueError("Pass checkout_request_id or account_reference.")

    params = {"checkout_request_id": checkout_request_id} if checkout_request_id else {"account_reference": account_reference}

    try:
        resp = requests.get(
            f"{_base_url()}/api/payment_status.php",
            params=params,
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as e:
        raise BluepayError(f"Could not reach BluePay: {e}")

    return _parse_json_response(resp)