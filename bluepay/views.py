"""
Single shared webhook endpoint for BluePay — both activation payments
and deposit payments land here, since one BluePay account has one
account-level callback URL (a per-STK callback_url override exists in
their API but we don't use it — one URL is simpler to keep correctly
configured in the dashboard than N of them).

Routing is done by account_reference prefix: "ACT-<id>" for an
ActivationSubmission, "DEP-<id>" for a DepositRequest — see
activation/views.py and payment/views.py for where those get built and
handed to bluepay.client.initiate_stk_push().
"""
import json
import logging

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .webhooks import verify_signature

logger = logging.getLogger(__name__)


class BluepayCallbackView(APIView):
    """
    POST /api/bluepay/callback/
    BluePay calls this directly — no user session involved, so this is
    deliberately AllowAny with no authentication classes (same reasoning
    payment.views.DarajaCallbackView used for Safaricom). Always returns
    HTTP 200 quickly — BluePay's own docs: "Return 2xx quickly. No
    automatic webhook retries — use payment status as backup." Failures
    are logged, not raised, so a bug on our side can't make BluePay (or
    an attacker replaying a bad payload) hammer this endpoint with
    retries that were never coming anyway.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request.body  # MUST read before request.data — see webhooks.verify_signature docstring
        signature = request.META.get("HTTP_X_BLUEPAY_SIGNATURE", "")

        if not verify_signature(raw_body, signature):
            logger.warning("BluePay webhook rejected: invalid/missing signature")
            return Response({"ok": False, "error": "Invalid signature"}, status=401)

        try:
            payload = json.loads(raw_body)
        except ValueError:
            logger.warning("BluePay webhook rejected: invalid JSON body")
            return Response({"ok": False, "error": "Invalid JSON"}, status=400)

        event = payload.get("event", "")
        data = payload.get("data", {}) or {}
        account_reference = str(data.get("account_reference") or "")

        try:
            if account_reference.startswith("ACT-"):
                self._handle_activation(event, data, account_reference)
            elif account_reference.startswith("DEP-"):
                self._handle_deposit(event, data, account_reference)
            else:
                logger.warning("BluePay webhook with unrecognized account_reference: %r", account_reference)
        except Exception:
            # Never let a bug here surface as a 5xx to BluePay — see class docstring.
            # payment_status polling (bluepay.client.check_payment_status) is the
            # backstop for anything that fails to process here.
            logger.exception("Error processing BluePay webhook payload: %s", payload)

        return Response({"ok": True})

    def _handle_activation(self, event, data, account_reference):
        # Local import — keeps bluepay a leaf app at import time (it has
        # no app-level dependency on activation/payment; only this
        # request-time handler reaches into them). activation/payment
        # import bluepay.client, never the other way round, so there's
        # no circular import either way.
        from activation.models import ActivationStatus, ActivationSubmission

        submission_id = account_reference[len("ACT-"):]
        submission = ActivationSubmission.objects.filter(
            pk=submission_id, status=ActivationStatus.PENDING
        ).first()
        if not submission:
            logger.warning("BluePay activation webhook for unknown/already-resolved submission: %s", account_reference)
            return

        submission.bluepay_receipt_number = str(data.get("mpesa_receipt_number", ""))
        submission.save(update_fields=["bluepay_receipt_number"])

        if event == "mpesa.payment.received" and data.get("status") == "success":
            submission.approve()
        elif event == "mpesa.payment.failed":
            submission.reject(notes="BluePay reported this payment as failed or cancelled.")

    def _handle_deposit(self, event, data, account_reference):
        from payment.models import DepositRequest, RequestStatus

        deposit_id = account_reference[len("DEP-"):]
        deposit = DepositRequest.objects.filter(pk=deposit_id, status=RequestStatus.PENDING).first()
        if not deposit:
            logger.warning("BluePay deposit webhook for unknown/already-resolved deposit: %s", account_reference)
            return

        deposit.bluepay_receipt_number = str(data.get("mpesa_receipt_number", ""))
        deposit.save(update_fields=["bluepay_receipt_number"])

        if event == "mpesa.payment.received" and data.get("status") == "success":
            deposit.approve()
        elif event == "mpesa.payment.failed":
            deposit.status = RequestStatus.REJECTED
            deposit.save(update_fields=["status"])