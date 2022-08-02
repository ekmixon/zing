# -*- coding: utf-8 -*-
#
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from collections.abc import Iterable


def flatten(elements):
    """Flatten a list of values and/or iterables.

    Source: http://stackoverflow.com/a/2158532/783019
    """
    for element in elements:
        if isinstance(element, Iterable) and not isinstance(element, str):
            yield from flatten(element)
        else:
            yield element
