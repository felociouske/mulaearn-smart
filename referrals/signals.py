from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from activation.models import ActivationStatus, ActivationSubmission
from plans.models import PlanPurchase
from wallets.models import Transaction
from .models import ReferralCommission, REFERRAL_ACTIVATION_COMMISSION_RATE, REFERRAL_COMMISSION_RATE


@receiver(post_save, sender=PlanPurchase)
def credit_referral_commission(sender, instance: PlanPurchase, created, **kwargs):
    """
    Every time a PlanPurchase is created, if the purchasing user was
    referred by someone, credit that referrer 70% of price_paid to their
    yield_balance — applies on upgrades too, since each PlanPurchase row
    is its own event (per your "even if they upgrade" instruction).
    """
    if not created:
        return

    referrer = instance.user.referred_by
    if not referrer:
        return

    commission_amount = (instance.price_paid * Decimal(str(REFERRAL_COMMISSION_RATE))).quantize(Decimal("0.01"))

    referrer.wallet.credit(
        wallet_type="yield",
        amount=commission_amount,
        transaction_type=Transaction.TransactionType.REFERRAL_COMMISSION,
        description=f"70% referral commission from {instance.user.username}'s {instance.plan.name} purchase",
    )

    ReferralCommission.objects.create(
        referrer=referrer,
        referred_user=instance.user,
        source=ReferralCommission.Source.PLAN_PURCHASE,
        plan_purchase=instance,
        amount=commission_amount,
    )


@receiver(post_save, sender=ActivationSubmission)
def credit_referral_activation_commission(sender, instance: ActivationSubmission, created, **kwargs):
    """
    Whenever an ActivationSubmission is saved with status APPROVED (i.e.
    ActivationSubmission.approve() was just called), if the newly
    activated user was referred by someone, credit that referrer 65% of
    the activation fee (`amount`) to their yield_balance.

    Guards against double-crediting with an existence check rather than
    relying on `created` — approve() updates an existing PENDING row
    (created=False), and status can only reach APPROVED once since
    approve() rejects re-approving an already-reviewed submission, but
    the existence check makes this safe even if that ever changes.
    """
    if instance.status != ActivationStatus.APPROVED:
        return

    referrer = instance.user.referred_by
    if not referrer:
        return

    if ReferralCommission.objects.filter(activation_submission=instance).exists():
        return

    commission_amount = (instance.amount * Decimal(str(REFERRAL_ACTIVATION_COMMISSION_RATE))).quantize(Decimal("0.01"))

    referrer.wallet.credit(
        wallet_type="yield",
        amount=commission_amount,
        transaction_type=Transaction.TransactionType.REFERRAL_COMMISSION,
        description=f"65% referral commission from {instance.user.username}'s account activation",
    )

    ReferralCommission.objects.create(
        referrer=referrer,
        referred_user=instance.user,
        source=ReferralCommission.Source.ACTIVATION,
        activation_submission=instance,
        amount=commission_amount,
    )