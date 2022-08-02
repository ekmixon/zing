# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import json

import pytest

from pootle_app.models.directory import Directory
from pootle_language.models import Language
from pootle_project.models import Project
from pootle_store.models import Store
from pootle_translationproject.models import TranslationProject

from pootle.core.utils.stats import get_top_scorers_data
from django.contrib.auth import get_user_model


def get_top_scorers_test_data(project_code, language_code):
    top_scorers = get_user_model().top_scorers(
        project=project_code, language=language_code,
    )

    return get_top_scorers_data(top_scorers, 5)


@pytest.mark.django_db
def test_get_contributors_store(client, request_users):

    user = request_users["user"]
    if user.username != "nobody":
        client.force_login(user)

    store = Store.objects.get(pootle_path="/language0/project0/store0.po")
    response = client.get(
        f"/xhr/stats/contributors/?path={store.pootle_path}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    result = json.loads(response.content)

    top_scorers_data = get_top_scorers_test_data(
        project_code=store.translation_project.project.code,
        language_code=store.translation_project.language.code,
    )
    for k, v in result.items():
        assert top_scorers_data[k] == v


@pytest.mark.django_db
def test_get_contributors_tp(client, request_users):

    user = request_users["user"]
    if user.username != "nobody":
        client.force_login(user)

    tp = TranslationProject.objects.get(pootle_path="/language0/project0/")
    response = client.get(
        f"/xhr/stats/contributors/?path={tp.pootle_path}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    result = json.loads(response.content)

    top_scorers_data = get_top_scorers_test_data(
        project_code=tp.project.code, language_code=tp.language.code
    )
    for k, v in result.items():
        assert top_scorers_data[k] == v


@pytest.mark.django_db
def test_get_contributors_project(client, request_users):

    user = request_users["user"]
    if user.username != "nobody":
        client.force_login(user)

    project = Project.objects.get(code="project0")
    response = client.get(
        f"/xhr/stats/contributors/?path={project.pootle_path}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    result = json.loads(response.content)

    top_scorers_data = get_top_scorers_test_data(
        project_code=project.code, language_code=None,
    )
    for k, v in result.items():
        assert top_scorers_data[k] == v


@pytest.mark.django_db
def test_get_contributors_language(client, request_users):

    user = request_users["user"]
    if user.username != "nobody":
        client.login(username=user.username, password=request_users["password"])

    language = Language.objects.get(code="language0")
    response = client.get(
        f"/xhr/stats/contributors/?path={language.pootle_path}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    result = json.loads(response.content)

    top_scorers_data = get_top_scorers_test_data(
        project_code=None, language_code=language.code
    )
    for k, v in result.items():
        assert top_scorers_data[k] == v


@pytest.mark.django_db
def test_get_contributors_projects(client, request_users):

    user = request_users["user"]
    if user.username != "nobody":
        client.login(username=user.username, password=request_users["password"])

    directory = Directory.objects.projects
    response = client.get(
        f"/xhr/stats/contributors/?path={directory.pootle_path}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    result = json.loads(response.content)

    top_scorers_data = get_top_scorers_test_data(project_code=None, language_code=None)
    for k, v in result.items():
        assert top_scorers_data[k] == v


@pytest.mark.parametrize(
    "path, offset",
    [("/TOO_LONG_PATH" * 200, 0), ("/language0/", "WRONG_OFFSET"), ("/language0/", -1)],
)
@pytest.mark.django_db
def test_get_contributors_wrong_params(client, request_users, path, offset):

    user = request_users["user"]
    if user.username != "nobody":
        client.force_login(user)

    response = client.get(
        f"/xhr/stats/contributors/?path={path}&offset={offset}",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 404
