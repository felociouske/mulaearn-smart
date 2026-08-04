from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from plans.models import PlanPurchase
from wallets.models import Transaction
from .models import ReferralCommission, REFERRAL_COMMISSION_RATE


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
        plan_purchase=instance,
        amount=commission_amount,
    )