# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import logging

from translate.misc.lru import LRUCachingDict

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property

from pootle.core.constants import PARSE_POOL_CULL_FREQUENCY, PARSE_POOL_SIZE
from pootle.core.mixins import CachedMethods, CachedTreeItem
from pootle.core.url_helpers import get_editor_filter, split_pootle_path
from pootle_app.models.directory import Directory
from pootle_app.project_tree import (
    does_not_exist,
    get_translation_project_dir,
    translation_project_dir_exists,
)
from pootle_language.models import Language
from pootle_misc.checks import excluded_filters
from pootle_project.models import Project
from pootle_store.constants import PARSED
from pootle_store.models import Store
from pootle_store.util import absolute_real_path, relative_real_path


class TranslationProjectNonDBState(object):
    def __init__(self, parent):
        self.parent = parent

        # Terminology matcher
        self.termmatcher = None
        self.termmatchermtime = None


def create_or_resurrect_translation_project(language, project):
    tp = create_translation_project(language, project)
    if tp is not None:
        if tp.directory.obsolete:
            tp.directory.obsolete = False
            tp.directory.save()
            logging.info(u"Resurrected %s", tp)
        else:
            logging.info(u"Created %s", tp)


def create_translation_project(language, project):
    if translation_project_dir_exists(language, project):
        try:
            translation_project, __ = TranslationProject.objects.all().get_or_create(
                language=language, project=project
            )
            return translation_project
        except (OSError, IndexError):
            return None


def scan_translation_projects(languages=None, projects=None):
    project_query = Project.objects.all()

    if projects is not None:
        project_query = project_query.filter(code__in=projects)

    for project in project_query.iterator():
        if does_not_exist(project.get_real_path()):
            logging.info(u"Disabling %s", project)
            project.disabled = True
            project.save()
        else:
            lang_query = Language.objects.exclude(
                id__in=project.translationproject_set.live().values_list(
                    "language", flat=True
                )
            )
            if languages is not None:
                lang_query = lang_query.filter(code__in=languages)

            for language in lang_query.iterator():
                create_or_resurrect_translation_project(language, project)


class TranslationProjectManager(models.Manager):
    def get_terminology_project(self, language_id):
        # FIXME: the code below currently uses the same approach to determine
        # the 'terminology' kind of a project as 'Project.is_terminology()',
        # which means it checks the value of 'checkstyle' field
        # (see pootle_project/models.py:240).
        #
        # This should probably be replaced in the future with a dedicated
        # project property.
        return self.get(language=language_id, project__checkstyle="terminology")

    def live(self):
        """Filters translation projects that have non-obsolete directories."""
        return self.filter(directory__obsolete=False)

    def disabled(self):
        """Filters translation projects that belong to disabled projects."""
        return self.filter(project__disabled=True)

    def for_user(self, user, include_disabled=False, select_related=None):
        """Filters translation projects for a specific user.

        - Admins always get all translation projects.
        - Regular users only get enabled translation projects
            accessible to them.

        :param user: The user for whom the translation projects need to be
            retrieved for.
        :param include_disabled: Whether to include disabled projects or not.
        :return: A filtered queryset with `TranslationProject`s for `user`.
        """
        qs = self.live()
        if select_related is not None:
            qs = qs.select_related(*select_related)

        if not include_disabled or not user.is_superuser:
            qs = qs.filter(project__disabled=False)

        if user.is_superuser:
            return qs

        return qs.filter(project__code__in=Project.accessible_by_user(user))

    def get_for_user(
        self,
        user,
        project_code,
        language_code,
        include_disabled=False,
        select_related=None,
    ):
        """Gets a `language_code`/`project_code` translation project
        for a specific `user`.

        - Admins can get the translation project even
            if its project is disabled.
        - Regular users only get a translation project
            if its project isn't disabled and it is accessible to them.

        :param user: The user for whom the translation project needs
            to be retrieved.
        :param project_code: The code of a project for the TP to retrieve.
        :param language_code: The code of the language fro the TP to retrieve.
        :param include_disabled: Whether to include disabled projects or not.
        :return: The `TranslationProject` matching the params, raises
            otherwise.
        """
        return self.for_user(user, include_disabled, select_related).get(
            project__code=project_code, language__code=language_code
        )


class TranslationProject(models.Model, CachedTreeItem):

    language = models.ForeignKey(Language, db_index=True, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, db_index=True, on_delete=models.CASCADE)
    real_path = models.FilePathField(editable=False, null=True, blank=True)
    directory = models.OneToOneField(
        Directory, db_index=True, editable=False, on_delete=models.CASCADE
    )
    pootle_path = models.CharField(
        max_length=255, null=False, unique=True, db_index=True, editable=False
    )
    creation_time = models.DateTimeField(
        auto_now_add=True, db_index=True, editable=False, null=True
    )

    _non_db_state_cache = LRUCachingDict(PARSE_POOL_SIZE, PARSE_POOL_CULL_FREQUENCY)

    objects = TranslationProjectManager()

    class Meta(object):
        unique_together = ("language", "project")
        db_table = "pootle_app_translationproject"
        base_manager_name = "objects"

    @cached_property
    def code(self):
        return u"-".join([self.language.code, self.project.code])

    # # # # # # # # # # # # # #  Properties # # # # # # # # # # # # # # # # # #

    @property
    def name(self):
        # TODO: See if `self.fullname` can be removed
        return self.fullname

    @property
    def fullname(self):
        return f"{self.project.fullname} [{self.language.name}]"

    @property
    def abs_real_path(self):
        if self.real_path is not None:
            return absolute_real_path(self.real_path)

    @abs_real_path.setter
    def abs_real_path(self, value):
        self.real_path = relative_real_path(value) if value is not None else None

    @property
    def checker(self):
        from translate.filters import checks

        # We do not use default Translate Toolkit checkers; instead use
        # our own one
        if settings.ZING_QUALITY_CHECKER:
            from pootle_misc.util import import_func

            checkerclasses = [import_func(settings.ZING_QUALITY_CHECKER)]
        else:
            checkerclasses = [
                checks.projectcheckers.get(
                    self.project.checkstyle, checks.StandardChecker
                )
            ]

        return checks.TeeChecker(
            checkerclasses=checkerclasses,
            excludefilters=excluded_filters,
            errorhandler=self.filtererrorhandler,
            languagecode=self.language.code,
        )

    @property
    def non_db_state(self):
        if not hasattr(self, "_non_db_state"):
            try:
                self._non_db_state = self._non_db_state_cache[self.id]
            except KeyError:
                self._non_db_state = TranslationProjectNonDBState(self)
                self._non_db_state_cache[self.id] = TranslationProjectNonDBState(self)

        return self._non_db_state

    @property
    def disabled(self):
        return self.project.disabled

    @property
    def is_terminology_project(self):
        return self.project.checkstyle == "terminology"

    # # # # # # # # # # # # # #  Methods # # # # # # # # # # # # # # # # # # #

    def __str__(self):
        return self.pootle_path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.directory = self.language.directory.get_or_make_subdir(self.project.code)
        self.pootle_path = self.directory.pootle_path

        self.abs_real_path = get_translation_project_dir(
            self.language,
            self.project.get_real_path(),
            make_dirs=not self.directory.obsolete,
        )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        directory = self.directory

        super().delete(*args, **kwargs)
        directory.delete()

    def get_absolute_url(self):
        return reverse(
            "pootle-tp-browse", args=split_pootle_path(self.pootle_path)[:-1]
        )

    def get_translate_url(self, **kwargs):
        return u"".join(
            [
                reverse(
                    "pootle-tp-translate", args=split_pootle_path(self.pootle_path)[:-1]
                ),
                get_editor_filter(**kwargs),
            ]
        )

    def filtererrorhandler(self, functionname, str1, str2, e):
        logging.error(u"Error in filter %s: %r, %r, %s", functionname, str1, str2, e)
        return False

    def is_accessible_by(self, user):
        """Returns `True` if the current translation project is accessible
        by `user`.
        """
        if user.is_superuser:
            return True

        return self.project.code in Project.accessible_by_user(user)

    def update_from_disk(self, force=False, overwrite=False):
        """Update all stores to reflect state on disk.

        :return: `True` if any of the existing stores were updated.
            FIXME note: `scan_files()` doesn't report whether something
            changed or not, but it can obsolete dirs/stores. Hence if that
            happened the return value will be `False`, which is misleading.
        """
        changed = False

        logging.info(u"Scanning for new files in %s", self)
        # Create new, make obsolete in-DB stores to reflect state on disk
        self.scan_files()

        stores = self.stores.live().select_related("parent").exclude(file="")
        # Update store content from disk store
        for store in stores.iterator():
            changed = (
                store.updater.update_from_disk(force=force, overwrite=overwrite)
                or changed
            )

        # If this TP has no stores, cache should be updated forcibly.
        if not changed and stores.count() == 0:
            self.update_all_cache()

        return changed

    def sync(self, conservative=True, skip_missing=False, only_newer=True):
        """Sync unsaved work on all stores to disk"""
        stores = self.stores.live().exclude(file="").filter(state__gte=PARSED)
        for store in stores.select_related("parent").iterator():
            store.sync(
                update_structure=not conservative,
                conservative=conservative,
                skip_missing=skip_missing,
                only_newer=only_newer,
            )

    # # # TreeItem
    def get_children(self):
        return self.directory.children

    def get_parent(self):
        return self.project

    # # # /TreeItem

    def directory_exists_on_disk(self):
        """Checks if the actual directory for the translation project
        exists on disk.
        """
        return not does_not_exist(self.abs_real_path)

    def scan_files(self):
        """Scans the file system and returns a list of translation files.
        """
        from pootle_app.project_tree import add_files

        all_files = []
        new_files = []

        all_files, new_files, __ = add_files(self, self.real_path, self.directory,)

        return all_files, new_files

    ###########################################################################

    def gettermmatcher(self):
        """Returns the terminology matcher."""
        terminology_stores = Store.objects.none()
        mtime = None

        if not self.is_terminology_project:
            # Get global terminology first
            try:
                termproject = TranslationProject.objects.get_terminology_project(
                    self.language_id
                )
                mtime = termproject.get_cached_value(CachedMethods.MTIME)
                terminology_stores = termproject.stores.live()
            except TranslationProject.DoesNotExist:
                pass

        if mtime is None:
            return

        if mtime != self.non_db_state.termmatchermtime:
            from pootle_misc.match import Matcher

            self.non_db_state.termmatcher = Matcher(terminology_stores.iterator())
            self.non_db_state.termmatchermtime = mtime

        return self.non_db_state.termmatcher
