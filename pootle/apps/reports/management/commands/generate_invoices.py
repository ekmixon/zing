#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.


import os

from datetime import datetime

# This must be run before importing Django.
os.environ["DJANGO_SETTINGS_MODULE"] = "pootle.settings"

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from pootle.core.utils.docs import get_docs_url

from ...models import Invoice
from ...reporters import JSONReporter


User = get_user_model()


class Command(BaseCommand):
    help = "Generate invoices and send them via e-mail."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            dest="user_list",
            help="Limit generating invoices to these users",
            nargs="*",
            default=[],
        )
        parser.add_argument(
            "--month",
            dest="month",
            help=(
                "Process invoices for the given month (YYYY-MM). By default "
                "the previous month will be used."
            ),
            default=None,
        )

        email_group = parser.add_argument_group(
            "E-mail", "Controls whether invoices are sent via e-mail and how.",
        )
        email_group.add_argument(
            "--send-emails",
            action="store_true",
            dest="send_emails",
            help="Send generated invoices by email",
            default=False,
        )
        email_group.add_argument(
            "--bcc",
            dest="bcc_email_list",
            help="Send email to the specified recipients as BCC",
            nargs="*",
            default=[],
        )
        email_group.add_argument(
            "--override-to",
            dest="to_email_list",
            help="Send email to recipients (overrides existing user settings)",
            nargs="*",
            default=[],
        )

        report_group = parser.add_argument_group(
            "Reporting", "Options for invoice-related reports.",
        )
        report_group.add_argument(
            "--generate-report",
            action="store_true",
            dest="generate_report",
            help="Generate a report of the invoicing job in JSON format.",
            default=False,
        )

    def handle(self, **options):
        send_emails = options["send_emails"]
        month = options["month"]
        if month is not None:
            try:
                month = datetime.strptime(month, "%Y-%m")
            except ValueError:
                raise CommandError(
                    '--month parameter has an invalid format: "%s", '
                    'while it should be in "YYYY-MM" format' % month
                )

        if not settings.ZING_INVOICES_RECIPIENTS:
            raise CommandError(
                "No invoicing configuration found, nothing to be done.\n\n"
                "Please read the docs at %s to learn more about how to "
                "use this feature." % (get_docs_url("features/invoices.html"),)
            )
        users = list(settings.ZING_INVOICES_RECIPIENTS.items())
        if options["user_list"]:
            users = [x for x in users if x[0] in options["user_list"]]

        # Abort if a user defined in the configuration does not exist or its
        # configuration is missing required fields
        user_dict = {}
        for username, user_conf in users:
            Invoice.check_config_for(
                user_conf, username, require_email_fields=send_emails
            )
            usernames = (username,) + user_conf.get("subcontractors", ())

            for username in usernames:
                if username in user_dict:
                    continue

                try:
                    user_dict[username] = User.objects.get(username=username)
                except User.DoesNotExist:
                    raise ImproperlyConfigured(f"User {username} not found.")

        reporter = JSONReporter()
        for username, user_conf in users:
            subcontractors = [
                user_dict[subcontractor_name]
                for subcontractor_name in user_conf.get("subcontractors", ())
            ]
            invoice = Invoice(
                user_dict[username],
                user_conf,
                month=month,
                subcontractors=subcontractors,
                add_correction=month is None,
            )
            reporter.add(invoice)

            fullname = user_conf["name"]

            self.stdout.write(f"Generating invoices for {fullname}...")
            invoice.generate()

            if not send_emails:
                continue

            self.stdout.write(f"Sending email to {fullname}...")
            # FIXME: reuse connections to the mail server
            # (http://stackoverflow.com/a/10215091/783019)
            if (
                invoice.send_by_email(
                    override_to=options["to_email_list"],
                    override_bcc=options["bcc_email_list"],
                )
                > 0
            ):
                self.stdout.write("Email sent")
            else:
                self.stdout.write("ERROR: sending failed")

        if options["generate_report"]:
            reporter.generate()
            self.stdout.write(f"JSON report written to {reporter.filepath}.")
