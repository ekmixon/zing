# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os

from django.conf import settings

from .constants import STATES_NAMES, TRANSLATED
from .unit.altsrc import AltSrcUnits


class SuggestionStates(object):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


def add_trailing_slash(path):
    """If path does not end with /, add it and return."""

    return path if len(path) > 0 and path[-1] == os.sep else path + os.sep


def relative_real_path(p):
    if p.startswith(settings.ZING_TRANSLATION_DIRECTORY):
        return p[len(add_trailing_slash(settings.ZING_TRANSLATION_DIRECTORY)) :]
    else:
        return p


def absolute_real_path(p):
    return (
        p
        if p.startswith(settings.ZING_TRANSLATION_DIRECTORY)
        else os.path.join(settings.ZING_TRANSLATION_DIRECTORY, p)
    )


def find_altsrcs(unit, alt_src_langs, store=None, project=None):
    from pootle_store.models import Unit

    if not alt_src_langs:
        return []

    store = store or unit.store
    project = project or store.translation_project.project

    language_regex = f'({"|".join([x.code for x in alt_src_langs])})'
    pootle_path = f"/{language_regex}/{project.code}/{store.path}$"

    altsrcs_qs = Unit.objects.filter(
        unitid_hash=unit.unitid_hash,
        store__pootle_path__regex=pootle_path,
        store__translation_project__project=project,
        store__translation_project__language__in=alt_src_langs,
        state=TRANSLATED,
    )

    return AltSrcUnits(altsrcs_qs).units


def get_change_str(changes):
    """Returns a formatted string for the non-zero items of a `changes`
    dictionary.

    If all elements are zero, `nothing changed` is returned.
    """
    if res := [
        u"%s %d" % (key, changes[key]) for key in changes if changes[key] > 0
    ]:
        return ", ".join(res)

    return "no changed"


def get_state_name(code, default="untranslated"):
    return STATES_NAMES.get(code, default)
