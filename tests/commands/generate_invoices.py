# -*- coding: utf-8 -*-
#
# Copyright (C) Zing contributors.
#
# This file is a part of the zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.cmd
@pytest.mark.parametrize("month", ["12-2012", "12-12", "12", "12/2012", "2012/12"])
def test_generate_invoices_invalid_month(month):
    with pytest.raises(CommandError) as e:
        call_command("generate_invoices", f"--month={month}")
    assert "month parameter has an invalid format" in str(e.value)


@pytest.mark.cmd
@pytest.mark.django_db
def test_generate_invoices_no_recipients_setting(settings):
    # Setting this to `None` is the same as having no setting at all
    settings.ZING_INVOICES_RECIPIENTS = None
    with pytest.raises(CommandError) as e:
        call_command("generate_invoices")
    assert "No invoicing configuration found" in str(e.value)


@pytest.mark.cmd
@pytest.mark.django_db
@pytest.mark.parametrize(
    "recipients, args",
    [
        (
            {"bogus_member": {"name": "foo", "paid_by": "foo", "wire_info": "foo"}},
            None,
        ),
        ({"member": {"paid_by": "foo", "wire_info": "foo"}}, None),
        (
            {"member": {"name": "foo", "paid_by": "foo", "wire_info": "foo"}},
            "--send-emails",
        ),
    ],
)
def test_generate_invoices_incomplete_config(settings, recipients, args):
    settings.ZING_INVOICES_RECIPIENTS = recipients
    with pytest.raises(ImproperlyConfigured):
        if args is None:
            call_command("generate_invoices")
        else:
            call_command("generate_invoices", args)


@pytest.mark.cmd
@pytest.mark.django_db
def test_generate_invoices_generate_report(settings, member, capfd, tmpdir):
    settings.ZING_INVOICES_RECIPIENTS = {
        "member": {"name": "foo", "paid_by": "foo", "wire_info": "foo"},
    }
    settings.ZING_INVOICES_DIRECTORY = tmpdir.strpath
    call_command("generate_invoices", "--generate-report")

    out, _ = capfd.readouterr()
    assert "JSON report written to" in out
