# -*- coding: utf-8 -*-
#
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from .models import LegalPage


NOCHECK_PREFIXES = (
    "/about",
    "/accounts",
    "/admin",
    "/contact",
    "/jsi18n",
    "/pages",
    "/xhr",
)


def agreement(request):
    """Returns whether the agreement box should be displayed or not."""
    request_path = request.META["PATH_INFO"]
    nocheck = [x for x in NOCHECK_PREFIXES if request_path.startswith(x)]

    display_agreement = bool(
        (
            request.user.is_authenticated
            and not nocheck
            and LegalPage.objects.has_pending_agreement(request.user)
        )
    )

    return {
        "display_agreement": display_agreement,
    }
