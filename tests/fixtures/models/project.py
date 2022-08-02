# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os
import shutil

import pytest


def _require_project(code, name, source_language, **kwargs):
    """Helper to get/create a new project."""
    from pootle_project.models import Project

    criteria = {
        "code": code,
        "fullname": name,
        "source_language": source_language,
        "checkstyle": "standard",
    } | kwargs

    return Project.objects.get_or_create(**criteria)[0]


@pytest.fixture
def tutorial(english, settings, data_dir):
    """Require `tutorial` test project."""
    shutil.copytree(
        data_dir("po", "tutorial"),
        os.path.join(settings.ZING_TRANSLATION_DIRECTORY, "tutorial"),
    )

    return _require_project("tutorial", "Tutorial", english)


@pytest.fixture
def tutorial_disabled(english):
    """Require `tutorial-disabled` test project in a disabled state."""
    return _require_project("tutorial-disabled", "Tutorial", english, disabled=True)


@pytest.fixture
def project_foo(english):
    """Require `foo` test project."""
    return _require_project("foo", "Foo Project", english)


@pytest.fixture
def project_bar(english):
    """Require `bar` test project."""
    return _require_project("bar", "Bar Project", english)


@pytest.fixture
def project0():
    """project0 Project"""
    from pootle_project.models import Project

    return Project.objects.get(code="project0")


@pytest.fixture
def project1():
    """project0 Project"""
    from pootle_project.models import Project

    return Project.objects.get(code="project1")


@pytest.fixture
def project0_directory(po_directory, project0):
    """project0 Project"""
    return project0


@pytest.fixture
def project0_disk(project0_directory, project0):
    """`project0` fixture but with on-disk directories and TPs."""
    project0.save()
    for tp in project0.translationproject_set.all():
        tp.save()
    return project0


@pytest.fixture
def project_dir_resources0(project0, subdir0):
    """Returns a ProjectResource object for a Directory"""

    from pootle_app.models import Directory
    from pootle_project.models import ProjectResource

    resources = Directory.objects.live().filter(
        name=subdir0.name, parent__translationproject__project=project0
    )
    return ProjectResource(resources, f"/projects/{project0.code}/{subdir0.name}")


@pytest.fixture
def project_store_resources0(project0, subdir0):
    """Returns a ProjectResource object for a Store"""

    from pootle_project.models import ProjectResource
    from pootle_store.models import Store

    store = subdir0.child_stores.live().first()
    resources = Store.objects.live().filter(
        name=store.name,
        parent__name=subdir0.name,
        translation_project__project=project0,
    )

    return ProjectResource(
        resources, f"/projects/{project0.code}/{subdir0.name}/{store.name}"
    )


@pytest.fixture
def project_set():
    from pootle_project.models import Project, ProjectSet

    return ProjectSet(Project.objects.exclude(disabled=True))
