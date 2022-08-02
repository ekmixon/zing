#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os
import re
import sys
from distutils import log
from distutils.command.build import build as DistutilsBuild
from distutils.errors import DistutilsOptionError

from setuptools import find_packages, setup

from pootle import __version__


def parse_requirements(file_name):
    """Parses a pip requirements file and returns a list of packages.

    Use the result of this function in the ``install_requires`` field.
    Copied from cburgmer/pdfserver.
    """
    requirements = []
    for line in open(file_name, "r").read().split("\n"):
        # Ignore comments, blank lines and included requirements files
        if re.match(
            r"(\s*#)|(\s*$)|" "((-r|--allow-external|--allow-unverified) .*$)", line
        ):
            continue

        if re.match(r"\s*-e\s+", line):
            requirements.append(re.sub(r"\s*-e\s+.*#egg=(.*)$", r"\1", line))
        elif not re.match(r"\s*-f\s+", line):
            requirements.append(line)

    return requirements


class PootleBuildMo(DistutilsBuild):

    description = "compile Gettext PO files into MO"
    user_options = [
        ("all", None, "compile all language (don't use LINGUAS file)"),
        ("lang=", "l", "specify a language to compile"),
        ("check", None, "check for errors"),
    ]
    boolean_options = ["all"]

    po_path_base = os.path.join("pootle", "locale")
    _langs = []

    def initialize_options(self):
        self.all = False
        self.lang = None
        self.check = False

    def finalize_options(self):
        if self.all and self.lang is not None:
            raise DistutilsOptionError("Can't use --all and --lang together")
        if self.lang is not None:
            self._langs = [self.lang]
        elif self.all:
            for lang in os.listdir(self.po_path_base):
                if (
                    os.path.isdir(os.path.join(self.po_path_base, lang))
                    and lang != "templates"
                ):
                    self._langs.append(lang)
        else:
            for lang in open(os.path.join("pootle", "locale", "LINGUAS")):
                self._langs.append(lang.rstrip())

    def build_mo(self):
        """Compile .mo files from available .po files"""
        import subprocess
        import gettext
        from translate.storage import factory

        error_occured = False

        for lang in self._langs:
            lang = lang.rstrip()

            po_path = os.path.join("pootle", "locale", lang)
            mo_path = os.path.join("pootle", "locale", lang, "LC_MESSAGES")

            if not os.path.exists(mo_path):
                os.makedirs(mo_path)

            for po, mo in (("pootle.po", "django.mo"), ("pootle_js.po", "djangojs.mo")):
                po_filename = os.path.join(po_path, po)
                mo_filename = os.path.join(mo_path, mo)

                if not os.path.exists(po_filename):
                    log.warn("%s: missing file %s", lang, po_filename)
                    continue

                if not os.path.exists(mo_path):
                    os.makedirs(mo_path)

                log.info("compiling %s", lang)
                if self.check:
                    command = [
                        "msgfmt",
                        "-c",
                        "--strict",
                        "-o",
                        mo_filename,
                        po_filename,
                    ]
                else:
                    command = ["msgfmt", "--strict", "-o", mo_filename, po_filename]
                try:
                    subprocess.check_call(command, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    error_occured = True
                except Exception as e:
                    log.warn("%s: skipping, running msgfmt failed: %s", lang, e)

                try:
                    store = factory.getobject(po_filename)
                    gettext.c2py(store.getheaderplural()[1])
                except Exception:
                    log.warn("%s: invalid plural header in %s", lang, po_filename)

        if error_occured:
            sys.exit(1)

    def run(self):
        self.build_mo()


setup(
    name="Zing",
    version=__version__,
    description="An online interface to localizing.",
    long_description=open(
        os.path.join(os.path.dirname(__file__), "README.md")
    ).read(),
    author="Evernote",
    author_email="l10n-developers@evernote.com",
    license="GNU General Public License 3 or later (GPLv3+)",
    url="https://github.com/evernote/zing",
    download_url=f"https://github.com/evernote/zing/releases/tag/{__version__}",
    install_requires=parse_requirements("requirements/base.txt"),
    platforms=["any"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: "
        "GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Localization",
        "Topic :: Text Processing :: Linguistic",
    ],
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    entry_points={"console_scripts": ["zing = pootle.runner:main"]},
    cmdclass={"build_mo": PootleBuildMo},
)
