# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import locale
from collections import OrderedDict
from operator import itemgetter

from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pootle.core.cache import make_method_key
from pootle.core.constants import CACHE_TIMEOUT
from pootle.core.mixins import TreeItem
from pootle.core.url_helpers import get_editor_filter
from pootle.i18n.gettext import language_dir, tr_lang


class LiveLanguageManager(models.Manager):
    """Manager that only considers `live` languages.

    A live language is any language containing at least a project with
    translatable files.
    """

    def get_queryset(self):
        """Returns a queryset for all live languages for enabled projects."""
        return (
            super()
            .get_queryset()
            .filter(
                translationproject__isnull=False,
                translationproject__directory__obsolete=False,
                translationproject__project__disabled=False,
            )
            .distinct()
        )

    def get_all_queryset(self):
        """Returns a queryset for all live languages for all projects."""
        return (
            super()
            .get_queryset()
            .filter(
                translationproject__isnull=False,
                translationproject__directory__obsolete=False,
            )
            .distinct()
        )

    def cached_dict(self, locale_code="en-us", show_all=False):
        """Retrieves a sorted list of live language codes and names.

        By default only returns live languages for enabled projects, but it can
        also return live languages for disabled projects if specified.

        :param locale_code: the UI locale for which language full names need to
            be localized.
        :param show_all: tells whether to return all live languages (both for
            disabled and enabled projects) or only live languages for enabled
            projects.
        :return: an `OrderedDict`
        """
        key_prefix = "all_cached_dict" if show_all else "cached_dict"
        key = make_method_key(self, key_prefix, locale_code)
        languages = cache.get(key, None)
        if languages is None:
            qs = self.get_all_queryset() if show_all else self.get_queryset()
            languages = OrderedDict(
                sorted(
                    [
                        (locale.strxfrm(lang[0]), tr_lang(lang[1]))
                        for lang in qs.values_list("code", "fullname")
                    ],
                    key=itemgetter(0),
                )
            )
            cache.set(key, languages, CACHE_TIMEOUT)

        return languages


class Language(models.Model, TreeItem):

    # any changes to the `code` field may require updating the schema
    # see migration 0002_case_insensitive_schema.py
    code = models.CharField(
        max_length=50,
        null=False,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_(
            "ISO 639 language code for the language, possibly "
            "followed by an underscore (_) and an ISO 3166 country "
            'code. <a href="http://www.w3.org/International/'
            'articles/language-tags/">More information</a>'
        ),
    )
    fullname = models.CharField(max_length=255, null=False, verbose_name=_("Full Name"))

    specialchars = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Special Characters"),
        help_text=_(
            "Enter any special characters that users might find " "difficult to type"
        ),
    )

    plurals_help_text = _(
        "For more information, visit "
        '<a href="http://docs.translatehouse.org/projects/'
        "localization-guide/en/latest/l10n/"
        'pluralforms.html">'
        "our page</a> on plural forms."
    )
    nplural_choices = (
        (0, _("Unknown")),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
    )
    nplurals = models.SmallIntegerField(
        default=0,
        choices=nplural_choices,
        verbose_name=_("Number of Plurals"),
        help_text=plurals_help_text,
    )
    pluralequation = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Plural Equation"),
        help_text=plurals_help_text,
    )

    directory = models.OneToOneField(
        "pootle_app.Directory", db_index=True, editable=False, on_delete=models.CASCADE
    )

    objects = models.Manager()
    live = LiveLanguageManager()

    class Meta(object):
        ordering = ["code"]
        db_table = "pootle_app_language"

    # # # # # # # # # # # # # #  Properties # # # # # # # # # # # # # # # # # #

    @property
    def pootle_path(self):
        return f"/{self.code}/"

    @property
    def name(self):
        """Localized fullname for the language."""
        return tr_lang(self.fullname)

    @property
    def direction(self):
        """Return the language direction."""
        return language_dir(self.code)

    # # # # # # # # # # # # # #  Methods # # # # # # # # # # # # # # # # # # #

    @classmethod
    def get_canonical(cls, language_code):
        """Returns the canonical `Language` object matching `language_code`.

        If no language can be matched, `None` will be returned.

        :param language_code: the code of the language to retrieve.
        """
        try:
            return cls.objects.get(code__iexact=language_code)
        except cls.DoesNotExist:
            _lang_code = language_code
            if "-" in language_code:
                _lang_code = language_code.replace("-", "_")
            elif "_" in language_code:
                _lang_code = language_code.replace("_", "-")
            try:
                return cls.objects.get(code__iexact=_lang_code)
            except cls.DoesNotExist:
                return None

    def __str__(self):
        return f"{self.name} - {self.code}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.fullname}>"

    def save(self, *args, **kwargs):
        # create corresponding directory object
        from pootle_app.models.directory import Directory

        self.directory = Directory.objects.root.get_or_make_subdir(self.code)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        directory = self.directory
        super().delete(*args, **kwargs)
        directory.delete()

    def get_absolute_url(self):
        return reverse("pootle-language-browse", args=[self.code])

    def get_translate_url(self, **kwargs):
        return u"".join(
            [
                reverse("pootle-language-translate", args=[self.code]),
                get_editor_filter(**kwargs),
            ]
        )

    def clean(self):
        super().clean()

        if self.fullname:
            self.fullname = self.fullname.strip()

    # # # TreeItem

    def get_children(self):
        return self.translationproject_set.live()

    # # # /TreeItem

    def get_stats_for_user(self, user, include_disabled=False):
        self.set_children(
            self.get_children_for_user(user, include_disabled=include_disabled)
        )
        return self.get_stats()

    def get_children_for_user(self, user, include_disabled=False, select_related=None):
        return self.translationproject_set.for_user(
            user, include_disabled=include_disabled, select_related=select_related
        ).select_related("project")


def clear_language_list_cache():
    key = make_method_key("LiveLanguageManager", "cached_dict", "*")
    cache.delete_pattern(key)

    key_all = make_method_key("LiveLanguageManager", "all_cached_dict", "*")
    cache.delete_pattern(key_all)


@receiver([post_delete, post_save])
def invalidate_language_list_cache(**kwargs):
    instance = kwargs["instance"]
    # XXX: maybe use custom signals or simple function calls?
    if instance.__class__.__name__ not in ["Language", "TranslationProject"]:
        return

    clear_language_list_cache()
