# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models
from django.utils.encoding import iri_to_uri

from pootle.core.constants import CACHE_TIMEOUT


def get_permission_contenttype():
    return ContentType.objects.filter(
        app_label="pootle_app", model="directory"
    )[0]


def get_pootle_permission(codename):
    # The content type of our permission
    content_type = get_permission_contenttype()
    # Get the pootle view permission
    return Permission.objects.get(content_type=content_type, codename=codename)


def get_permissions_by_username(username, directory):
    pootle_path = directory.pootle_path
    path_parts = [_f for _f in pootle_path.split("/") if _f]
    key = iri_to_uri(f"Permissions:{username}")
    permissions_cache = cache.get(key, {})

    if pootle_path not in permissions_cache:
        try:
            permissionset = PermissionSet.objects.filter(
                directory__in=directory.trail(), user__username=username
            ).order_by("-directory__pootle_path")[0]
        except IndexError:
            permissionset = None

        if (
            len(path_parts) > 1
            and path_parts[0] != "projects"
            and (
                permissionset is None
                or len(
                    [_f for _f in permissionset.directory.pootle_path.split("/") if _f]
                )
                < 2
            )
        ):
            # Active permission at language level or higher, check project
            # level permission
            try:
                project_path = f"/projects/{path_parts[1]}/"
                permissionset = PermissionSet.objects.get(
                    directory__pootle_path=project_path, user__username=username
                )
            except PermissionSet.DoesNotExist:
                pass

        if permissionset:
            permissions_cache[pootle_path] = permissionset.to_dict()
        else:
            permissions_cache[pootle_path] = None

        cache.set(key, permissions_cache, CACHE_TIMEOUT)

    return permissions_cache[pootle_path]


def get_matching_permissions(user, directory):
    if user.is_authenticated:
        permissions = get_permissions_by_username(user.username, directory)
        if permissions is not None:
            return permissions

        permissions = get_permissions_by_username("default", directory)
        if permissions is not None:
            return permissions

    permissions = get_permissions_by_username("nobody", directory)

    return permissions


def check_user_permission(user, permission_codename, directory):
    """Checks if the current user has the permission to perform
    ``permission_codename``.
    """
    if user.is_superuser:
        return True

    permissions = get_matching_permissions(user, directory)

    return "administrate" in permissions or permission_codename in permissions


def check_permission(permission_codename, request):
    """Checks if the current user has `permission_codename`
    permissions.
    """
    if request.user.is_superuser:
        return True

    # `view` permissions are project-centric, and we must treat them
    # differently
    if permission_codename == "view":
        path_obj = None
        if hasattr(request, "translation_project"):
            path_obj = request.translation_project
        elif hasattr(request, "project"):
            path_obj = request.project

        return True if path_obj is None else path_obj.is_accessible_by(request.user)
    return (
        "administrate" in request.permissions
        or permission_codename in request.permissions
    )


class PermissionSet(models.Model):
    class Meta(object):
        unique_together = ("user", "directory")
        app_label = "pootle_app"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_index=True, on_delete=models.CASCADE
    )
    directory = models.ForeignKey(
        "pootle_app.Directory",
        db_index=True,
        related_name="permission_sets",
        on_delete=models.CASCADE,
    )
    positive_permissions = models.ManyToManyField(
        Permission, db_index=True, related_name="permission_sets_positive"
    )
    negative_permissions = models.ManyToManyField(
        Permission, db_index=True, related_name="permission_sets_negative"
    )

    def __str__(self):
        return f"{self.user.username} : {self.directory.pootle_path}"

    def to_dict(self):
        permissions_iterator = self.positive_permissions.iterator()
        return {perm.codename: perm for perm in permissions_iterator}

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # FIXME: can we use `post_save` signals or invalidate caches in model
        # managers, please?
        key = iri_to_uri(f"Permissions:{self.user.username}")
        cache.delete(key)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # FIXME: can we use `post_delete` signals or invalidate caches in model
        # managers, please?
        key = iri_to_uri(f"Permissions:{self.user.username}")
        cache.delete(key)
