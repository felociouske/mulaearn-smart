from rest_framework.permissions import BasePermission


class IsActivated(BasePermission):
    """
    Blocks any view for users who haven't activated their account yet.
    Stack this alongside IsAuthenticated (it assumes the user is already
    authenticated — checking request.user.is_activated on an anonymous
    user would just be False anyway, but pair it with IsAuthenticated for
    a clearer 401 vs 403 distinction).

    Used now on task/plan-purchase endpoints; wire it into chat/reviews
    views too as those get built out.
    """
    message = "Activate your account before accessing this feature."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_activated
        )
