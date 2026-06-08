

from rest_framework import permissions
from rest_framework.permissions import BasePermission
from rest_framework.permissions import SAFE_METHODS, BasePermission





class IsPlatformAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role == "platform_admin"
            )
        )



class IsCustomer(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "customer"
        )



class IsOwnerOrReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.method in SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        owner_fields = [
            "owner",
            "user",
            "customer",
        ]

        for field in owner_fields:
            if hasattr(obj, field):
                return getattr(obj, field) == request.user

        return False




# class IsOwnerOrReadOnly(BasePermission):

#     def has_object_permission(self, request, view, obj):

#         if request.user.is_superuser:
#             return True

#         if request.method in SAFE_METHODS:
#             return True

#         return obj.customer == request.user




# class IsOwnerOrReadOnly(permissions.BasePermission):
#     """
#     Custom permission to only allow owners of an object to edit it.
#     Supports objects with fields: organizer, user, or owner.
#     """
#     def has_object_permission(self, request, view, obj):
#         # Read permissions are allowed to any request
#         if request.method in permissions.SAFE_METHODS:
#             return True

#         # Vérifie les différents noms de champ propriétaire possibles
#         if hasattr(obj, 'organizer') and obj.organizer == request.user:
#             return True
#         if hasattr(obj, 'user') and obj.user == request.user:
#             return True
#         if hasattr(obj, 'owner') and obj.owner == request.user:
#             return True
#         if hasattr(obj, 'event') and hasattr(obj.event, 'organizer') and obj.event.organizer == request.user:
#             return True
#         return False