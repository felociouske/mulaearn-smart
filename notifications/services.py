from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Broadcast, Notification
from .push import push_refresh_to_everyone

BATCH_SIZE = 1000


def send_broadcast(broadcast: Broadcast) -> int:
    """
    Fans a Broadcast out to every active user as individual Notification rows.
    bulk_create in batches keeps memory flat and is fast enough for tens of
    thousands of users; move it to a Celery task only if you outgrow that.
    Returns how many users were notified.
    """
    User = get_user_model()
    user_ids = User.objects.filter(is_active=True).values_list("id", flat=True).iterator(chunk_size=BATCH_SIZE)

    sent = 0
    batch = []
    with transaction.atomic():
        for user_id in user_ids:
            batch.append(Notification(
                user_id=user_id,
                type=broadcast.type,
                title=broadcast.title,
                message=broadcast.message,
                link=broadcast.link,
                expires_at=broadcast.expires_at,
            ))
            if len(batch) >= BATCH_SIZE:
                Notification.objects.bulk_create(batch)
                sent += len(batch)
                batch = []
        if batch:
            Notification.objects.bulk_create(batch)
            sent += len(batch)

        Broadcast.objects.filter(pk=broadcast.pk).update(sent_count=sent)
        broadcast.sent_count = sent
        # bulk_create does NOT fire post_save, so nudge every open socket once
        # (after commit, so the refetch is guaranteed to see the new rows).
        transaction.on_commit(push_refresh_to_everyone)

    return sent


def notify(user, type, title, message, *, amount=None, currency_code="", link="", expires_at=None):
    """
    Public helper for any app that needs to notify one user, e.g. from
    payment/views.py when a deposit is rejected:

        from notifications.services import notify
        notify(user, "deposit", "Deposit failed", "Your M-Pesa payment was not completed.")

    Creating the row is enough — the post_save receiver in signals.py handles the live push.
    """
    return Notification.objects.create(
        user=user, type=type, title=title, message=message,
        amount=amount, currency_code=currency_code, link=link, expires_at=expires_at,
    )