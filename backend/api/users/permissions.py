from rest_framework import permissions
from django.conf import settings


class IsUserOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return str(obj.id) == str(request.user.id)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a category to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return str(obj.user.id) == str(request.user.id)


class IsCategoryOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission for categories: everyone may read categories in
    their queryset (own + global), but only the owning user may edit or delete.
    Global categories (category_owner_user is None) are read-only for everyone.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if obj.category_owner_user_id is None:
            return False
        return str(obj.category_owner_user_id) == str(request.user.id)

