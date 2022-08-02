# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import json
import operator
from functools import reduce

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, Q
from django.forms.models import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import View

from pootle.core.http import (
    JsonResponse,
    JsonResponseBadRequest,
    JsonResponseForbidden,
    JsonResponseNotFound,
)


class JSONDecodeError(ValueError):
    pass


class APIView(View):
    """View to implement internal RESTful APIs.

    Based on djangbone https://github.com/af/djangbone
    """

    # Model on which this view operates. Setting this is required
    model = None

    # Base queryset for accessing data. If `None`, model's default manager will
    # be used
    base_queryset = None

    # Set this to restrict the view to a subset of the available methods
    restrict_to_methods = None

    # Field names to be included
    fields = ()

    # Individual forms to use for each method. By default it'll auto-populate
    # model forms built using `self.model` and `self.fields`
    add_form_class = None
    edit_form_class = None

    # Permission classes implement logic to determine whether the request
    # should be permitted. Empty list means no permission-checking.
    permission_classes = []

    # Tuple of sensitive field names that will be excluded from any serialized
    # responses
    sensitive_field_names = ("password", "pw")

    # Set to an integer to enable GET pagination
    page_size = None

    # HTTP GET parameter to use for accessing pages
    page_param_name = "p"

    # HTTP GET parameter to use for search queries
    search_param_name = "q"

    # Field names in which searching will be allowed
    search_fields = None

    @property
    def allowed_methods(self):
        methods = [m for m in self.http_method_names if hasattr(self, m)]

        if self.restrict_to_methods is not None:
            restricted_to = [x.lower() for x in self.restrict_to_methods]
            methods = [x for x in methods if x in restricted_to]

        return methods

    def __init__(self, *args, **kwargs):
        if self.model is None:
            raise ValueError("No model class specified.")

        self.pk_field_name = self.model._meta.pk.name

        if self.base_queryset is None:
            self.base_queryset = self.model._default_manager

        self._init_fields()
        self._init_forms()

        return super().__init__(*args, **kwargs)

    def _init_fields(self):
        if len(self.fields) < 1:
            form = self.add_form_class or self.edit_form_class
            if form is not None:
                self.fields = form._meta.fields
            else:  # Assume all fields by default
                self.fields = (f.name for f in self.model._meta.fields)

        self.serialize_fields = (
            f for f in self.fields if f not in self.sensitive_field_names
        )

    def _init_forms(self):
        if "post" in self.allowed_methods and self.add_form_class is None:
            self.add_form_class = modelform_factory(self.model, fields=self.fields)

        if "put" in self.allowed_methods and self.edit_form_class is None:
            self.edit_form_class = modelform_factory(self.model, fields=self.fields)

    @cached_property
    def request_data(self):
        try:
            return json.loads(self.request.body)
        except ValueError:
            raise JSONDecodeError

    def get_permissions(self):
        """Returns permission handler instances required for a particular view."""
        return [permission() for permission in self.permission_classes]

    def check_permissions(self, request):
        """Checks whether the view is allowed to process the request or not.
        """
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                raise PermissionDenied

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                raise PermissionDenied

    def handle_exception(self, exc):
        """Handles response exceptions."""
        if isinstance(exc, Http404):
            return JsonResponseNotFound({"msg": "Not found"})

        if isinstance(exc, PermissionDenied):
            return JsonResponseForbidden({"msg": "Permission denied."})

        if isinstance(exc, JSONDecodeError):
            return JsonResponseBadRequest({"msg": "Invalid JSON data"})

        raise

    def dispatch(self, request, *args, **kwargs):
        try:
            self.check_permissions(request)

            if request.method.lower() in self.allowed_methods:
                handler = getattr(
                    self, request.method.lower(), self.http_method_not_allowed
                )
            else:
                handler = self.http_method_not_allowed

            return handler(request, *args, **kwargs)
        except Exception as exc:
            return self.handle_exception(exc)

    def get(self, request, *args, **kwargs):
        """GET handler."""
        if self.kwargs.get(self.pk_field_name, None) is not None:
            object = self.get_object()
            return JsonResponse(self.object_to_values(object))

        return self.get_collection(request, *args, **kwargs)

    def get_object(self):
        """Returns a single model instance."""
        obj = get_object_or_404(self.base_queryset, pk=self.kwargs[self.pk_field_name],)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_collection(self, request, *args, **kwargs):
        """Retrieve a full collection."""
        return JsonResponse(self.qs_to_values(self.base_queryset))

    def get_form_kwargs(self):
        kwargs = {
            "data": self.request_data,
        }
        if (
            self.pk_field_name in self.kwargs
            and self.kwargs[self.pk_field_name] is not None
        ):
            kwargs["instance"] = self.get_object()

        return kwargs

    def post(self, request, *args, **kwargs):
        """Creates a new model instance.

        The form to be used can be customized by setting
        `self.add_form_class`. By default a model form will be used with
        the fields from `self.fields`.
        """
        form = self.add_form_class(**self.get_form_kwargs())

        if form.is_valid():
            new_object = form.save()
            return JsonResponse(self.object_to_values(new_object))

        return self.form_invalid(form)

    def put(self, request, *args, **kwargs):
        """Update the current model."""
        if self.pk_field_name not in self.kwargs:
            return self.status_msg("PUT is not supported for collections", status=405)

        form = self.edit_form_class(**self.get_form_kwargs())

        if form.is_valid():
            updated_object = form.save()
            return JsonResponse(self.object_to_values(updated_object))

        return self.form_invalid(form)

    def delete(self, request, *args, **kwargs):
        """Delete the model and return its JSON representation."""
        if self.pk_field_name not in kwargs:
            return self.status_msg(
                "DELETE is not supported for collections", status=405
            )

        obj = self.get_object()
        try:
            obj.delete()
            return JsonResponse({})
        except ProtectedError as e:
            return self.status_msg(str(e), status=405)

    def object_to_values(self, object):
        """Convert an object to values for serialization."""
        return {field: getattr(object, field) for field in self.serialize_fields}

    def qs_to_values(self, queryset):
        """Convert a queryset to values for further serialization.

        An array of objects in `models` and the total object count in
        `count` is returned.
        """
        search_keyword = self.request.GET.get(self.search_param_name, None)
        if search_keyword is not None:
            filter_by = self.get_search_filter(search_keyword)
            queryset = queryset.filter(filter_by)

        values = queryset.values(*self.serialize_fields)

        # Process pagination options if they are enabled
        if isinstance(self.page_size, int):
            try:
                page_param = self.request.GET.get(self.page_param_name, 1)
                page_number = int(page_param)
                offset = (page_number - 1) * self.page_size
            except ValueError:
                offset = 0

            values = values[offset : offset + self.page_size]

        return {
            "models": list(values),
            "count": queryset.count(),
        }

    def get_search_filter(self, keyword):
        search_fields = getattr(self, "search_fields", None)
        if search_fields is None:
            search_fields = self.fields  # Assume all fields

        field_queries = list(
            zip(
                map(lambda x: f"{x}__icontains", search_fields),
                (keyword,) * len(search_fields),
            )
        )

        lookups = [Q(x) for x in field_queries]

        return reduce(operator.or_, lookups)

    def status_msg(self, msg, status=400):
        return JsonResponse({"msg": msg}, status=status)

    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors}, status=400)
