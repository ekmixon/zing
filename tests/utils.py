# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

"""Random utilities for tests."""

import io

from translate.storage.factory import getclass


STRING_STORE = """
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"X-Generator: Pootle Tests\\n"

%(units)s
"""

STRING_UNIT = """
#: %(src)s
msgid "%(src)s"
msgstr "%(target)s"
"""


def setup_store(pootle_path):
    from pootle.core.url_helpers import split_pootle_path
    from pootle_translationproject.models import TranslationProject

    from .factories import StoreDBFactory

    (lang_code, proj_code, dir_path, filename) = split_pootle_path(pootle_path)
    tp = TranslationProject.objects.get(
        language__code=lang_code, project__code=proj_code
    )
    directory = tp.directory.get_relative(dir_path)

    return StoreDBFactory(translation_project=tp, parent=directory, name=filename)


def create_store(units=None):
    _units = [
        STRING_UNIT % {"src": src, "target": target}
        for src, target in units or []
    ]

    units = "\n\n".join(_units)
    string_store = STRING_STORE % {"units": units}
    io_store = io.BytesIO(string_store.encode("utf-8"))
    return getclass(io_store)(io_store.read())


def get_test_uids(offset=0, count=1, pootle_path="^/language0/"):
    """Returns a list translated unit uids from ~middle of
    translated units dataset
    """
    from pootle_store.constants import TRANSLATED
    from pootle_store.models import Unit

    units = Unit.objects.filter(store__pootle_path__regex=pootle_path).filter(
        state=TRANSLATED
    )
    begin = (units.count() / 2) + offset
    return list(units[begin : begin + count].values_list("pk", flat=True))


def items_equal(left, right):
    """Returns `True` if items in `left` list are equal to items in
    `right` list.
    """
    return sorted(left) == sorted(right)


def create_api_request(
    rf, method="get", url="/", data="", user=None, encode_as_json=True
):
    """Convenience function to create and setup fake requests."""
    content_type = "application/x-www-form-urlencoded"
    if data and encode_as_json:
        from pootle.core.utils.json import jsonify

        content_type = "application/json"
        data = jsonify(data)

    request_method = getattr(rf, method.lower())
    request = request_method(url, data=data, content_type=content_type)
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"

    if user is not None:
        request.user = user

    return request


def update_store(
    store, units=None, store_revision=None, user=None, submission_type=None
):
    store.update(
        store=create_store(units=units),
        store_revision=store_revision,
        user=user,
        submission_type=submission_type,
    )


def as_dir(name):
    """Returns `name` as a string usable for snapshot stacks."""
    return name if name.endswith("/") else f"{name}/"


def url_name(url):
    """Returns `url` as a string usable for snapshot stacks."""
    return url.replace("/", "_")
