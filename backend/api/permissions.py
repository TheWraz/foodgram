from rest_framework import permissions


class RecipePermission(permissions.BasePermission):
    """Разрешение для рецептов."""

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.method == 'POST' and request.user.is_authenticated
            or request.method not in ['POST']
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )


class UserPermission(permissions.BasePermission):
    """Разрешение для пользователей."""

    def has_permission(self, request, view):
        return (
            view.action in ['create', 'list', 'retrieve']
            or request.user.is_authenticated
        )
