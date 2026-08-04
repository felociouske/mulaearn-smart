"""
Safaricom Daraja integration for instant till-number deposits (Lipa Na
M-Pesa Online / STK Push, Buy Goods variant).

This is TILL-SPECIFIC: TransactionType is "CustomerBuyGoodsOnline" and
PartyB is the till number itself — different from a Paybill integration
(which would use "CustomerPayBillOnline" and a separate account number).
If this ever needs to also accept Paybill payments, that's a second
function, not a flag on this one — the request shape actually differs.

Required env vars (see mulaearn_backend/settings.py for the exact names):
  DARAJA_ENV                 "sandbox" or "production"
  DARAJA_CONSUMER_KEY
  DARAJA_CONSUMER_SECRET
  DARAJA_TILL_NUMBER          your Buy Goods till number
  DARAJA_PASSKEY              the Lipa Na M-Pesa Online passkey for that till
  DARAJA_CALLBACK_URL         full public HTTPS URL Safaricom will POST to —
                               e.g. https://your-api.up.railway.app/api/payments/deposits/daraja-callback/
                               Safaricom cannot reach localhost — test this
                               with ngrok (or Railway's own URL) even in sandbox.
"""
import base64
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

CACHE_KEY_ACCESS_TOKEN = "daraja_access_token"


class DarajaError(Exception):
    """Raised for any non-success response from Daraja — callers should catch this, not requests.HTTPError directly."""


def _base_url():
    return PRODUCTION_BASE_URL if settings.DARAJA_ENV == "production" else SANDBOX_BASE_URL


def get_access_token():
    """
    OAuth token, cached until ~1 minute before Safaricom's own expiry
    (normally 3599s) so we're not hitting the token endpoint on every
    single STK push request.
    """
    cached = cache.get(CACHE_KEY_ACCESS_TOKEN)
    if cached:
        return cached

    resp = requests.get(
        f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials",
        auth=(settings.DARAJA_CONSUMER_KEY, settings.DARAJA_CONSUMER_SECRET),
        timeout=10,
    )
    if not resp.ok:
        raise DarajaError(f"Daraja OAuth failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 3599))
    cache.set(CACHE_KEY_ACCESS_TOKEN, token, timeout=max(expires_in - 60, 60))
    return token


def _normalize_phone(phone_number):
    """
    Daraja wants MSISDN format: 2547XXXXXXXX (12 digits, no + or leading 0).
    Accepts the common Kenyan formats users might have stored:
    0712345678, +254712345678, 254712345678, 712345678.
    """
    digits = "".join(c for c in phone_number if c.isdigit())
    if digits.startswith("0"):
        return "254" + digits[1:]
    if digits.startswith("254"):
        return digits
    if len(digits) == 9:  # bare "712345678"
        return "254" + digits
    return digits


def initiate_stk_push(phone_number, amount, account_reference, transaction_desc="MulaEarn Deposit"):
    """
    Triggers the STK push — the user gets a prompt on their phone to enter
    their M-Pesa PIN. Returns Daraja's immediate response (contains
    CheckoutRequestID, which the caller must store to match the eventual
    callback to the right DepositRequest). Amount must be a whole number
    of KES — Daraja doesn't accept decimals.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{settings.DARAJA_TILL_NUMBER}{settings.DARAJA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.DARAJA_TILL_NUMBER,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": int(amount),
        "PartyA": _normalize_phone(phone_number),
        "PartyB": settings.DARAJA_TILL_NUMBER,
        "PhoneNumber": _normalize_phone(phone_number),
        "CallBackURL": settings.DARAJA_CALLBACK_URL,
        "AccountReference": str(account_reference)[:12],
        "TransactionDesc": transaction_desc[:13],
    }

    resp = requests.post(
        f"{_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=15,
    )
    data = resp.json()
    if not resp.ok or data.get("ResponseCode") != "0":
        raise DarajaError(data.get("errorMessage") or data.get("ResponseDescription") or "STK push failed")

    return data