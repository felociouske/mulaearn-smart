from django.db import models


class ChatProfile(models.Model):
    """
    A foreign client profile, added by you (the admin) — NOT a self-service
    user account. Users browse these at /chatting and start a chat with one.

    ASSUMPTION FLAGGED FOR YOUR REVIEW: we still don't have a confirmed rule
    for exactly how much a user earns per individual message vs per session —
    you gave a per-profile payout RANGE ($40-$800), not a per-message rate.
    For now `rate_per_message_kes` is a separate, explicitly-set field (defaults
    to None/unconfigured) so nothing pays out until you set a real number per
    profile. Flag this back to me once you've decided the mechanic and I'll
    wire the ChatMessage credit logic to match exactly.
    """
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="chat_profiles/", blank=True, null=True)
    bio = models.TextField(blank=True)

    # The advertised "amount on their profile" — shown to users browsing
    # /chatting. Stored in USD since you gave the range in dollars.
    payout_amount_usd = models.DecimalField(max_digits=8, decimal_places=2)

    # How much a user actually earns (in KES) per message sent in a session
    # with this profile. Left nullable on purpose — see docstring above.
    rate_per_message_kes = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    # Manually toggled by whichever staff member is actively covering this
    # profile right now (via the admin) — there's no automatic presence
    # detection since replies are typed by a real person in the admin,
    # not a persistent client connection. last_seen_at updates automatically
    # whenever a reply is sent (see ChatMessage.save()), so it works the
    # same way WhatsApp's "last seen" does even when is_online is off.
    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payout_amount_usd"]  # ascending — this ordering is what plan unlocks are ranked against

    def __str__(self):
        return f"{self.name} (${self.payout_amount_usd})"


def get_unlocked_profiles_for(user):
    """
    Returns the queryset of ChatProfiles a user currently has access to,
    based on their active CHAT-category plan's unlocked_item_count — the N
    lowest-paying active profiles, ascending, per your "4 lowest paying,
    upwards" rule.
    """
    from plans.models import PlanCategory, get_active_plan  # local import avoids a hard app-load-order dependency

    plan = get_active_plan(user, PlanCategory.CHAT)
    if not plan:
        return ChatProfile.objects.none()

    return ChatProfile.objects.filter(is_active=True).order_by("payout_amount_usd")[: plan.unlocked_item_count]