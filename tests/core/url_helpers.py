# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from pootle.core.url_helpers import (
    get_all_pootle_paths,
    get_editor_filter,
    split_pootle_path,
    urljoin,
)


def test_urljoin():
    """Tests URL parts are properly joined with a base."""
    base = "https://www.evernote.com/"
    assert urljoin(base) == base
    assert urljoin(base, "/foo/bar", "baz/blah") == f"{base}foo/bar/baz/blah"
    assert urljoin(base, "/foo/", "/bar/", "/baz/") == f"{base}foo/bar/baz/"
    assert urljoin(base, "/foo//", "//bar/") == f"{base}foo/bar/"
    assert urljoin(base, "/foo//", "//bar/?q=a") == f"{base}foo/bar/?q=a"
    assert urljoin(base, "foo//", "//bar/?q=a") == f"{base}foo/bar/?q=a"
    assert urljoin(base, "foo//////") == f"{base}foo/"
    assert urljoin(base, "foo", "bar/baz", "blah") == f"{base}foo/bar/baz/blah"
    assert urljoin(base, "foo/", "bar", "baz/") == f"{base}foo/bar/baz/"
    assert urljoin("", "", "/////foo") == "/foo"


def test_get_all_pootle_paths():
    """Tests all paths are properly extracted."""
    assert get_all_pootle_paths("") == [""]
    assert get_all_pootle_paths("/") == ["/"]
    assert get_all_pootle_paths("/projects/") == ["/projects/"]
    assert get_all_pootle_paths("/projects/tutorial/") == ["/projects/tutorial/"]
    assert get_all_pootle_paths("/pt/tutorial/") == [
        "/pt/tutorial/",
        "/projects/tutorial/",
    ]
    assert get_all_pootle_paths("/pt/tutorial/tutorial.po") == [
        "/pt/tutorial/tutorial.po",
        "/pt/tutorial/",
        "/projects/tutorial/",
    ]


def test_split_pootle_path():
    """Tests pootle path are properly split."""
    assert split_pootle_path("") == (None, None, "", "")
    assert split_pootle_path("/projects/") == (None, None, "", "")
    assert split_pootle_path("/projects/tutorial/") == (None, "tutorial", "", "")
    assert split_pootle_path("/pt/tutorial/tutorial.po") == (
        "pt",
        "tutorial",
        "",
        "tutorial.po",
    )
    assert split_pootle_path("/pt/tutorial/foo/tutorial.po") == (
        "pt",
        "tutorial",
        "foo/",
        "tutorial.po",
    )


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (dict(state="untranslated"), "#filter=untranslated"),
        (dict(state="untranslated", sort="newest"), "#filter=untranslated&sort=newest"),
        (dict(sort="newest"), "#sort=newest"),
        (dict(state="all", search="Foo", sfields="locations"), "#filter=all"),
        (dict(search="Foo", sfields="locations"), "#search=Foo&sfields=locations"),
        (
            dict(search="Foo", sfields=["locations", "notes"]),
            "#search=Foo&sfields=locations,notes",
        ),
        (
            dict(search="Foo: bar.po\nID: 1", sfields="locations"),
            "#search=Foo%3A+bar.po%0AID%3A+1&sfields=locations",
        ),
        (dict(include_disabled=False), ""),
        (dict(include_disabled=True), "#all"),
        (dict(state="translated", include_disabled=False), "#filter=translated"),
        (dict(state="translated", include_disabled=True), "#filter=translated&all"),
    ],
)
def test_get_editor_filter(kwargs, expected):
    """Tests editor filters are correctly constructed."""
    assert get_editor_filter(**kwargs) == expected
