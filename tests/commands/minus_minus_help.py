# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from django.core.management import call_command, get_commands

CORE_APPS_WITH_COMMANDS = (
    "accounts",
    "pootle_app",
)


@pytest.mark.cmd
@pytest.mark.parametrize(
    "command,app",
    [
        (command, app)
        for command, app in iter(get_commands().items())
        if app.startswith("pootle_") or app in CORE_APPS_WITH_COMMANDS
    ],
)
def test_initdb_help(capfd, command, app):
    """Catch any simple command issues"""
    print(f"Command: {command}, App: {app}")
    with pytest.raises(SystemExit):
        call_command(command, "--help")
    out, err = capfd.readouterr()
    assert "--help" in out
