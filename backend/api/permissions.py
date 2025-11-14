from rest_framework import permissions


class RecipePermission(permissions.BasePermission):
    """Разрешение для рецептов."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'POST':
            return request.user.is_authenticated
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class UserPermission(permissions.BasePermission):
    """Разрешение для пользователей."""

    def has_permission(self, request, view):
        if view.action in ['create', 'list', 'retrieve']:
            return True
        return request.user.is_authenticated
