# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from itertools import groupby

from django.forms import ValidationError
from django.http import Http404

from pootle.core.helpers import get_filter_name
from pootle_store.forms import UnitExportForm
from pootle_store.unit.search import DBSearchBackend

from .base import PootleDetailView


# Limit export view results to this amount of units
UNITS_LIMIT = 1000


class PootleExportView(PootleDetailView):
    template_name = "editor/export_view.html"

    @property
    def path(self):
        return self.request.path.replace("export-view/", "")

    def get_context_data(self, *args, **kwargs):
        ctx = {}
        filter_name, filter_extra = get_filter_name(self.request.GET)

        form_data = self.request.GET.copy()
        form_data["path"] = self.path
        form_data["include_disabled"] = "all" in self.request.GET

        search_form = UnitExportForm(form_data, user=self.request.user)

        if not search_form.is_valid():
            raise Http404(ValidationError(search_form.errors).messages)

        total, start_, end_, units_qs = DBSearchBackend(
            self.request.user, **search_form.cleaned_data
        ).search(limit=UNITS_LIMIT)

        units_qs = units_qs.select_related("store")

        if total > UNITS_LIMIT:
            ctx |= {"unit_total_count": total, "displayed_unit_count": UNITS_LIMIT}

        unit_groups = [
            (path, list(units))
            for path, units in groupby(units_qs, lambda x: x.store.pootle_path)
        ]

        ctx |= {
            "unit_groups": unit_groups,
            "filter_name": filter_name,
            "filter_extra": filter_extra,
            "source_language": self.source_language,
            "language": self.language,
            "project": self.project,
        }

        return ctx
