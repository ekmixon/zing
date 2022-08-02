# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from django.core.exceptions import ValidationError

from tests.factories import UserFactory
from tests.fixtures.models.permission_set import _require_permission_set
from tests.utils import items_equal

from pootle_project.models import Project, RESERVED_PROJECT_CODES


@pytest.mark.django_db
def test_create_project_good(english):
    """Tests projects are created with valid arguments only."""

    proj = Project(code="hello", fullname="world", source_language=english)
    proj.save()
    proj.delete()

    code_with_padding = "  hello  "
    fullname_with_padding = "  world  "

    proj = Project(code=code_with_padding, fullname="world", source_language=english)
    proj.save()
    assert proj.code == code_with_padding.strip()
    proj.delete()

    proj = Project(
        code="hello", fullname=fullname_with_padding, source_language=english
    )
    proj.save()
    assert proj.fullname == fullname_with_padding.strip()
    proj.delete()

    proj = Project(
        code=code_with_padding, fullname=fullname_with_padding, source_language=english
    )
    proj.save()
    assert proj.code == code_with_padding.strip()
    assert proj.fullname == fullname_with_padding.strip()
    proj.delete()


@pytest.mark.django_db
def test_create_project_bad(english):
    """Tests projects are not created with bad arguments."""

    with pytest.raises(ValidationError):
        Project().save()

    with pytest.raises(ValidationError):
        Project(code="hello").save()

    with pytest.raises(ValidationError):
        Project(fullname="world").save()

    with pytest.raises(ValidationError):
        Project(source_language=english).save()

    with pytest.raises(ValidationError):
        Project(code="hello", fullname="world").save()

    with pytest.raises(ValidationError):
        Project(code="hello", source_language=english).save()

    with pytest.raises(ValidationError):
        Project(fullname="world", source_language=english).save()

    with pytest.raises(ValidationError):
        Project(code="", fullname="world", source_language=english).save()

    with pytest.raises(ValidationError):
        Project(code="hello", fullname="", source_language=english).save()

    with pytest.raises(ValidationError):
        Project(code="  ", fullname="world", source_language=english).save()

    with pytest.raises(ValidationError):
        Project(code="hello", fullname="  ", source_language=english).save()


@pytest.mark.parametrize("reserved_code", RESERVED_PROJECT_CODES)
@pytest.mark.django_db
def test_create_project_reserved_code(english, reserved_code):
    """Tests projects are not created with reserved project codes."""

    with pytest.raises(ValidationError):
        Project(code=reserved_code, fullname="whatever", source_language=english).save()

    reserved_code_with_padding = f"  {reserved_code}  "
    with pytest.raises(ValidationError):
        Project(
            code=reserved_code_with_padding,
            fullname="whatever",
            source_language=english,
        ).save()


@pytest.mark.django_db
def test_project_save_no_code(project0):
    """Test that an existing project can't be removed its code."""
    project0.code = ""
    with pytest.raises(ValidationError):
        project0.save()


@pytest.mark.django_db
def test_project_save_no_fullname(project0):
    """Test that an existing project can't be removed its fullname."""
    project0.fullname = ""
    with pytest.raises(ValidationError):
        project0.save()


@pytest.mark.django_db
def test_no_root_view_permissions(
    po_directory,
    nobody,
    default,
    admin,
    view,
    no_permission_sets,
    no_projects,
    project_foo,
    project_bar,
):
    """Tests user-accessible projects when there are no permissions set at
    the root.
    """
    ALL_PROJECTS = [project_foo.code, project_bar.code]

    foo_user = UserFactory.create(username="foo")
    bar_user = UserFactory.create(username="bar")

    # By setting explicit `view` permissions for `foo_user` in `project_foo`,
    # only `foo_user` will be able to access that project
    _require_permission_set(foo_user, project_foo.directory, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(foo_user), [project_foo.code])
    assert items_equal(Project.accessible_by_user(bar_user), [])
    assert items_equal(Project.accessible_by_user(default), [])
    assert items_equal(Project.accessible_by_user(nobody), [])

    # Now let's allow showing `project_bar` to all registered users, but keep
    # `project_foo` visible only to `foo_user`.
    _require_permission_set(default, project_bar.directory, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(foo_user), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(bar_user), [project_bar.code])
    assert items_equal(Project.accessible_by_user(default), [project_bar.code])
    assert items_equal(Project.accessible_by_user(nobody), [])


@pytest.mark.django_db
def test_root_view_permissions(
    po_directory,
    nobody,
    default,
    admin,
    view,
    no_projects,
    no_permission_sets,
    project_foo,
    project_bar,
    root,
):
    """Tests user-accessible projects with view permissions at the root."""
    ALL_PROJECTS = [project_foo.code, project_bar.code]

    foo_user = UserFactory.create(username="foo")
    bar_user = UserFactory.create(username="bar")

    # We'll only give `bar_user` access to all projects server-wide
    _require_permission_set(bar_user, root, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(bar_user), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(foo_user), [])
    assert items_equal(Project.accessible_by_user(default), [])
    assert items_equal(Project.accessible_by_user(nobody), [])

    # Now we'll also allow `foo_user` access `project_foo`
    _require_permission_set(foo_user, project_foo.directory, [view])

    assert items_equal(Project.accessible_by_user(foo_user), [project_foo.code])

    # Let's change server-wide defaults: all registered users have access to
    # all projects. `foo_user`, albeit having explicit access for
    # `project_foo`, will be able to access any project because they fall back
    # and extend with the defaults.
    _require_permission_set(default, root, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(foo_user), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(bar_user), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(default), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(nobody), [])

    # Let's give anonymous users access to all projects too
    _require_permission_set(nobody, root, [view])

    assert items_equal(Project.accessible_by_user(nobody), ALL_PROJECTS)


@pytest.mark.django_db
def test_no_root_hide_permissions(
    po_directory,
    nobody,
    default,
    admin,
    hide,
    view,
    no_projects,
    no_permission_sets,
    project_foo,
    project_bar,
    root,
):
    """Tests user-accessible projects when there are no `hide` permissions
    set at the root.
    """

    ALL_PROJECTS = [project_foo.code, project_bar.code]

    foo_user = UserFactory.create(username="foo")
    bar_user = UserFactory.create(username="bar")

    # By default everyone has access to projects
    _require_permission_set(default, root, [view])
    _require_permission_set(nobody, root, [view])

    # At the same time, `project_foo` is inaccessible registered users...
    _require_permission_set(default, project_foo.directory, negative_permissions=[hide])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(default), [project_bar.code])
    assert items_equal(Project.accessible_by_user(nobody), [project_bar.code])
    assert items_equal(Project.accessible_by_user(foo_user), [project_bar.code])
    assert items_equal(Project.accessible_by_user(bar_user), [project_bar.code])

    # ...and anonymous users as well
    _require_permission_set(nobody, project_foo.directory, negative_permissions=[hide])

    assert items_equal(Project.accessible_by_user(nobody), [project_bar.code])

    # Let's make `project_foo` accessible for `foo_user`
    _require_permission_set(foo_user, project_foo.directory, [view])

    assert items_equal(Project.accessible_by_user(foo_user), ALL_PROJECTS)

    # `project_bar` is now inaccessible for anonymous users
    _require_permission_set(nobody, project_bar.directory, negative_permissions=[hide])

    assert items_equal(Project.accessible_by_user(nobody), [])


@pytest.mark.django_db
def test_root_hide_permissions(
    po_directory,
    nobody,
    default,
    admin,
    hide,
    view,
    no_permission_sets,
    no_projects,
    project_foo,
    project_bar,
    root,
):
    """Tests user-accessible projects when there are `hide` permissions
    set at the root.
    """

    ALL_PROJECTS = [project_foo.code, project_bar.code]

    foo_user = UserFactory.create(username="foo")
    bar_user = UserFactory.create(username="bar")

    # By default all projects are not accessible
    _require_permission_set(default, root, negative_permissions=[hide])
    _require_permission_set(nobody, root, negative_permissions=[hide])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(default), [])
    assert items_equal(Project.accessible_by_user(nobody), [])
    assert items_equal(Project.accessible_by_user(foo_user), [])
    assert items_equal(Project.accessible_by_user(bar_user), [])

    # Now let's make `project_foo` accessible to `foo_user`.
    _require_permission_set(foo_user, project_foo.directory, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(default), [])
    assert items_equal(Project.accessible_by_user(nobody), [])
    assert items_equal(Project.accessible_by_user(foo_user), [project_foo.code])
    assert items_equal(Project.accessible_by_user(bar_user), [])

    # Making projects accessible for anonymous users should open the door for
    # everyone
    _require_permission_set(nobody, root, [view])

    assert items_equal(Project.accessible_by_user(admin), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(default), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(nobody), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(foo_user), ALL_PROJECTS)
    assert items_equal(Project.accessible_by_user(bar_user), ALL_PROJECTS)
