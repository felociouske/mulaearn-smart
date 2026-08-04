from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        # Registers the post_save signal that auto-creates a Wallet for
        # every new user — imported here (not at module top) to avoid
        # circular imports between accounts and wallets at startup.
        import accounts.signals