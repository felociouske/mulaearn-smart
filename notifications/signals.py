import logging

from django.db import transaction
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from payment.models import DepositRequest, PaymentMethod, RequestStatus, WithdrawalRequest
from wallets.models import Transaction

from .models import Notification, NotificationType
from .push import push_notification

logger = logging.getLogger(__name__)

TT = Transaction.TransactionType

# Chat pays out on EVERY message, so notifying each one would flood the bell.
# Flip to True only if you want one notification per chat message.
NOTIFY_CHAT_EARNINGS = False

# Where tapping an auto-notification opens in the React app, by notification
# type. These match the routes in your App.tsx; an unlisted type simply isn't clickable.
LINKS = {
    "survey": "/survey",
    "wheel": "/wheel",
    "movie_review": "/movie-reviews",
    "app_review": "/app-reviews",
    "chat": "/chats",
    "referral": "/referrals",
    "loan": "/loans/history",
    "plan": "/wallet",
    "deposit": "/wallet",
    "withdrawal": "/wallet",
    "refund": "/wallet",
}

WALLET_LABELS = {"deposit": "Deposit Wallet", "account": "Account Balance", "yield": "Yield Wallet"}


def _create_safely(**fields):
    """
    Creates a Notification without ever being able to break the caller.
    The savepoint means a failure here rolls back ONLY this insert — the
    wallet credit / status change that triggered it must always survive.
    """
    try:
        with transaction.atomic():
            Notification.objects.create(**fields)
    except Exception:
        logger.exception("Could not create notification: %s", fields.get("title"))


# ---------------------------------------------------------------------------
# 1) Money events that go through the wallet ledger (earnings, loans, plans…)
# ---------------------------------------------------------------------------

# transaction_type -> (notification type, title, is it an "earning" message?)
#
# Deposits and withdrawals are deliberately NOT here: they're handled in
# section 2 from the request models themselves, because the request holds the
# amount in the currency the user actually entered, while the ledger stores
# the KES-converted figure (which would read wrong for non-Kenyan users) and
# the ledger can't see "requested" or "rejected" at all.
_SPECS = {
    TT.REFUND: (NotificationType.REFUND, "Refund received", False),
    TT.SURVEY_EARNING: (NotificationType.SURVEY, "Survey reward", True),
    TT.WHEEL_EARNING: (NotificationType.WHEEL, "Wheel spin win", True),
    TT.APP_REVIEW_EARNING: (NotificationType.APP_REVIEW, "App review reward", True),
    TT.MOVIE_REVIEW_EARNING: (NotificationType.MOVIE_REVIEW, "Movie review reward", True),
    TT.CHAT_EARNING: (NotificationType.CHAT, "Chat earning", True),
    TT.REFERRAL_COMMISSION: (NotificationType.REFERRAL, "Referral commission", True),
    TT.PLAN_PURCHASE: (NotificationType.PLAN, "Plan purchased", False),
    TT.LOAN_PLAN_PURCHASE: (NotificationType.LOAN, "Loan plan purchased", False),
    TT.LOAN_DISBURSEMENT: (NotificationType.LOAN, "Loan credited", False),
    TT.ADMIN_ADJUSTMENT: (NotificationType.SYSTEM, "Balance adjustment", False),
}


def _build_message(tx, symbol, is_earning):
    amount = abs(tx.amount)
    wallet = WALLET_LABELS.get(tx.wallet_type, tx.wallet_type)
    formatted = f"{symbol} {amount:,.2f}"

    if is_earning:
        message = f"You earned {formatted}."
    elif tx.amount > 0:
        message = f"{formatted} was added to your {wallet}."
    else:
        message = f"{formatted} was deducted from your {wallet}."

    # The ledger description carries the useful detail ("Survey 2026-09-30:
    # 8/10 correct", "Purchased Silver plan"), so reuse it rather than re-deriving it.
    # (Wheel descriptions only repeat the amount, so they're skipped.)
    if tx.description and tx.transaction_type != TT.WHEEL_EARNING:
        message = f"{message} {tx.description}"
    return message


@receiver(post_save, sender=Transaction)
def notify_on_transaction(sender, instance, created, **kwargs):
    """
    Every balance change goes through Wallet.credit()/debit(), which always
    writes a Transaction row — so listening here covers earnings, referral
    commission, plan + loan purchases and loan disbursements without touching
    any of those apps' views.
    """
    if not created:
        return

    spec = _SPECS.get(instance.transaction_type)
    if spec is None:
        return
    notif_type, title, is_earning = spec
    if notif_type == NotificationType.CHAT and not NOTIFY_CHAT_EARNINGS:
        return

    try:
        user = instance.wallet.user
        country = getattr(user, "country", None)
        symbol = country.currency_symbol if country else "KSh"
        currency_code = country.currency_code if country else "KES"
        message = _build_message(instance, symbol, is_earning)
    except Exception:
        logger.exception("Could not build notification for transaction %s", instance.pk)
        return

    _create_safely(
        user=user, type=notif_type, title=title, message=message,
        amount=instance.amount, currency_code=currency_code,
        link=LINKS.get(notif_type.value, ""),
    )


# ---------------------------------------------------------------------------
# 2) Deposit / withdrawal lifecycle (requested -> approved / rejected)
# ---------------------------------------------------------------------------
# We compare the status the row had when it was loaded with the status it's
# being saved with. That catches EVERY way a status can change — approve(),
# reject(), the BluePay webhook, an admin edit — without editing payment/.

@receiver(post_init, sender=DepositRequest)
@receiver(post_init, sender=WithdrawalRequest)
def remember_loaded_status(sender, instance, **kwargs):
    # __dict__ (not instance.status) so a .only()/.defer() query doesn't
    # trigger an extra database hit just to read the field.
    instance._notif_prev_status = instance.__dict__.get("status")


def _status_event(instance, created):
    """Returns "created", the new status string, or None when nothing relevant changed."""
    prev = getattr(instance, "_notif_prev_status", None)
    instance._notif_prev_status = instance.status
    if created:
        return "created"
    return instance.status if instance.status != prev else None


def _money(request_obj):
    return f"{request_obj.currency_code} {request_obj.amount:,.2f}"


@receiver(post_save, sender=DepositRequest)
def notify_on_deposit_change(sender, instance, created, **kwargs):
    event = _status_event(instance, created)
    if event is None:
        return

    money = _money(instance)
    link = LINKS.get("deposit", "")
    is_manual = instance.method == PaymentMethod.MANUAL
    base = dict(user=instance.user, type=NotificationType.DEPOSIT, currency_code=instance.currency_code, link=link)

    if event == "created":
        # Instant M-Pesa deposits are created and resolved within seconds while
        # the user is looking at the PIN prompt, so only manual ones get a
        # "submitted" message.
        if is_manual:
            _create_safely(
                **base, title="Deposit submitted",
                message=f"We received your deposit of {money}. It will be added to your Deposit Wallet once your payment is verified.",
            )
    elif event == RequestStatus.APPROVED:
        _create_safely(
            **base, title="Deposit received", amount=instance.amount,
            message=f"{money} has been added to your Deposit Wallet.",
        )
    elif event == RequestStatus.REJECTED:
        if is_manual:
            _create_safely(
                **base, title="Deposit rejected",
                message=f"We couldn't verify your deposit of {money}. If you did pay, contact support with your payment message.",
            )
        else:
            _create_safely(
                **base, title="Deposit not completed",
                message=f"Your M-Pesa payment of {money} wasn't completed, so nothing was added to your wallet.",
            )


@receiver(post_save, sender=WithdrawalRequest)
def notify_on_withdrawal_change(sender, instance, created, **kwargs):
    event = _status_event(instance, created)
    if event is None:
        return

    money = _money(instance)
    base = dict(
        user=instance.user, type=NotificationType.WITHDRAWAL,
        currency_code=instance.currency_code, link=LINKS.get("withdrawal", ""),
    )

    if event == "created":
        _create_safely(
            **base, title="Withdrawal requested",
            message=f"We received your request to withdraw {money}. You'll be notified once it's reviewed.",
        )
    elif event == RequestStatus.APPROVED:
        # Negative = money out, so the card shows in the "out" colour.
        _create_safely(
            **base, title="Withdrawal approved", amount=-instance.amount,
            message=f"Your withdrawal of {money} has been approved.",
        )
    elif event == RequestStatus.REJECTED:
        _create_safely(
            **base, title="Withdrawal rejected",
            message=f"Your withdrawal request of {money} was rejected. No funds were deducted from your wallet.",
        )


# ---------------------------------------------------------------------------
# 3) Live push for any new single-user notification
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Notification)
def push_on_notification_created(sender, instance, created, **kwargs):
    """
    on_commit: the push only goes out once the row is really committed, and
    never for a transaction that later rolls back.
    """
    if created:
        transaction.on_commit(lambda: push_notification(instance))