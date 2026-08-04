from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from wallets.models import Wallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    """
    Guarantees every user has exactly one Wallet from the moment they're
    created — nothing downstream (chat credits, task credits, deposits)
    has to defensively check "does this user have a wallet yet?".
    """
    if created:
        Wallet.objects.get_or_create(user=instance)