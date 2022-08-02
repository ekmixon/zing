# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from hashlib import md5

import factory

from django.utils import timezone

import pootle_store
from pootle.core.utils.timezone import make_aware


class ScoreLogFactory(factory.django.DjangoModelFactory):
    creation_time = make_aware(timezone.now())

    class Meta(object):
        model = "pootle_statistics.ScoreLog"


class SubmissionFactory(factory.django.DjangoModelFactory):
    creation_time = make_aware(timezone.now())

    class Meta(object):
        model = "pootle_statistics.Submission"




class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"foo{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.org")

    class Meta(object):
        model = "accounts.User"





class LegalPageFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f"title{n}")
    virtual_path = factory.Sequence(lambda n: f"/foo/bar{n}")

    class Meta(object):
        model = "staticpages.LegalPage"



class StaticPageFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "staticpages.StaticPage"


class AgreementFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    document = factory.SubFactory(LegalPageFactory)

    class Meta(object):
        model = "staticpages.Agreement"


class DirectoryFactory(factory.django.DjangoModelFactory):
    @factory.lazy_attribute
    def pootle_path(self):
        if self.parent is None:
            return "/"
        return f'{self.parent.pootle_path.rstrip("/")}/{self.name}'

    class Meta(object):
        model = "pootle_app.Directory"
        django_get_or_create = ("name", "parent")

    obsolete = False


class LanguageDBFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_language.Language"
        django_get_or_create = ("code",)

    nplurals = 2

    @factory.lazy_attribute
    def code(self):
        from pootle_language.models import Language

        # returns an incrementing index relative to the tp
        return f"language{Language.objects.count() - 1}"

    @factory.lazy_attribute
    def fullname(self):
        from pootle_language.models import Language

        # returns an incrementing index relative to the tp
        return f"Language {Language.objects.count() - 1}"


class ProjectDBFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_project.Project"
        django_get_or_create = ("code",)

    @factory.lazy_attribute
    def code(self):
        from pootle_project.models import Project

        # returns an incrementing index relative to the tp
        return f"project{Project.objects.count()}"

    @factory.lazy_attribute
    def fullname(self):
        from pootle_project.models import Project

        # returns an incrementing index relative to the tp
        return f"Project {Project.objects.count()}"

    checkstyle = "standard"


class StoreDBFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_store.Store"
        django_get_or_create = ("pootle_path",)

    parent = factory.LazyAttribute(lambda s: s.translation_project.directory)
    obsolete = False

    @factory.lazy_attribute
    def pootle_path(self):
        return f'{self.translation_project.pootle_path.rstrip("/")}/{self.name}'

    @factory.lazy_attribute
    def name(self):
        # returns an incrementing index relative to the tp
        return f"store{self.translation_project.stores.count()}.po"


class TranslationProjectFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_translationproject.TranslationProject"
        django_get_or_create = ("language", "project")


class UnitDBFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_store.Unit"

    state = pootle_store.constants.UNTRANSLATED

    @factory.lazy_attribute
    def index(self):
        # returns an incrementing index relative to the store
        return self.store.unit_set.count()

    @factory.lazy_attribute
    def unitid(self):
        return self.source_f

    @factory.lazy_attribute
    def unitid_hash(self):
        return md5(self.unitid.encode("utf-8")).hexdigest()

    @factory.lazy_attribute
    def source_f(self):
        is_terminology = self.store.translation_project.is_terminology_project
        state_name = pootle_store.util.get_state_name(self.state).capitalize()
        return f'{state_name + ((is_terminology and " Terminology" or ""))} Source {self.store.pootle_path} {self.index}%s.'

    @factory.lazy_attribute
    def target_f(self):
        state_name = pootle_store.util.get_state_name(self.state)
        endings = [" ", "", "%d", "\t"]
        if state_name in ["translated", "fuzzy", "obsolete"]:
            # make half fail checks
            ending = "%s." if self.index % 2 else endings[self.index % 4]
            return f"{state_name.capitalize()} Target {self.store.pootle_path} {self.index}{ending}"

        return ""

    @factory.lazy_attribute
    def source_wordcount(self):
        return pootle_store.models.count_words(self.source_f)

    @factory.lazy_attribute
    def target_wordcount(self):
        return pootle_store.models.count_words(self.target_f)


class SuggestionFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "pootle_store.Suggestion"


class DueDateFactory(factory.django.DjangoModelFactory):
    due_on = timezone.now()
    modified_by = factory.SubFactory(UserFactory)
    pootle_path = "/foo/"

    class Meta(object):
        model = "pootle.DueDate"


class PaidTaskFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = "reports.PaidTask"
