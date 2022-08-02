# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os
from collections import OrderedDict

import pytest

from django.utils import timezone

from tests.utils import create_store, update_store


DEFAULT_STORE_UNITS_1 = [
    ("Unit 1", "Unit 1"),
    ("Unit 2", "Unit 2"),
]

DEFAULT_STORE_UNITS_2 = [
    ("Unit 3", "Unit 3"),
    ("Unit 4", "Unit 4"),
    ("Unit 5", "Unit 5"),
]

DEFAULT_STORE_UNITS_3 = [
    ("Unit 6", "Unit 6"),
    ("Unit 7", "Unit 7"),
    ("Unit 8", "Unit 8"),
]

UPDATED_STORE_UNITS_1 = [
    (src, f"UPDATED {target}") for src, target in DEFAULT_STORE_UNITS_1
]


UPDATED_STORE_UNITS_2 = [
    (src, f"UPDATED {target}") for src, target in DEFAULT_STORE_UNITS_2
]


UPDATED_STORE_UNITS_3 = [
    (src, f"UPDATED {target}") for src, target in DEFAULT_STORE_UNITS_3
]


DEFAULT_STORE_TEST_SETUP = [
    (DEFAULT_STORE_UNITS_1),
    (DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2),
]

# The `UPDATE_STORE_TESTS` ordered dict takes the following shape:
#
#   * 'setup' key: indicates the setup steps to be performed:
#       `update_stores` will be run for each item in this list.
#       This makes it possible to make assertions on revisions afterwards.
#
#       The value of this key must contain a list of lists, where each
#       contained list has a two-tuple with the source and target
#       text values.
#
#       If no setup is provided, the `DEFAULT_STORE_TEST_SETUP` will be
#       used in `_setup_store_test()`.
#
#   * 'store_revision' key: indicates the last sync revision to be
#       considered for a store. The value can either be an actual number,
#       or `MAX` or `MID`. In the latter case, the actual revision number
#       will be calculated in the `_setup_store_test()` function,
#       which will then be used by actual fixtures before handing
#       the actual revision to tests.
#
#   * 'units_in_file' key: contains the updated units from the file
#       which will be handed to the actual tests before doing any
#       assertions.

UPDATE_STORE_TESTS = OrderedDict()
UPDATE_STORE_TESTS["min_empty"] = {
    "store_revision": -1,
    "units_in_file": [],
}
UPDATE_STORE_TESTS["min_new_units"] = {
    "store_revision": -1,
    "units_in_file": DEFAULT_STORE_UNITS_3,
}

UPDATE_STORE_TESTS["old_empty"] = {
    "store_revision": "MID",
    "units_in_file": [],
}
UPDATE_STORE_TESTS["old_subset_1"] = {
    "store_revision": "MID",
    "units_in_file": UPDATED_STORE_UNITS_1,
}
UPDATE_STORE_TESTS["old_subset_2"] = {
    "store_revision": "MID",
    "units_in_file": UPDATED_STORE_UNITS_2,
}
UPDATE_STORE_TESTS["old_same_updated"] = {
    "store_revision": "MID",
    "units_in_file": UPDATED_STORE_UNITS_1 + UPDATED_STORE_UNITS_2,
}

UPDATE_STORE_TESTS["old_unobsolete"] = {
    "setup": [DEFAULT_STORE_UNITS_1, DEFAULT_STORE_UNITS_2, []],
    "store_revision": "MID",
    "units_in_file": UPDATED_STORE_UNITS_1 + UPDATED_STORE_UNITS_2,
}

UPDATE_STORE_TESTS["old_merge"] = {
    "store_revision": "MID",
    "units_in_file": UPDATED_STORE_UNITS_1 + UPDATED_STORE_UNITS_2,
}

UPDATE_STORE_TESTS["max_empty"] = {
    "store_revision": "MAX",
    "units_in_file": [],
}
UPDATE_STORE_TESTS["max_subset"] = {
    "store_revision": "MAX",
    "units_in_file": DEFAULT_STORE_UNITS_1,
}
UPDATE_STORE_TESTS["max_same"] = {
    "store_revision": "MAX",
    "units_in_file": DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2,
}
UPDATE_STORE_TESTS["max_new_units"] = {
    "store_revision": "MAX",
    "units_in_file": (
        DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2 + DEFAULT_STORE_UNITS_3
    ),
}
UPDATE_STORE_TESTS["max_change_order"] = {
    "store_revision": "MAX",
    "units_in_file": DEFAULT_STORE_UNITS_2 + DEFAULT_STORE_UNITS_1,
}
UPDATE_STORE_TESTS["max_unobsolete"] = {
    "setup": [DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2, DEFAULT_STORE_UNITS_1],
    "store_revision": "MAX",
    "units_in_file": DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2,
}


UPDATE_STORE_TESTS["max_obsolete"] = {
    "setup": [
        DEFAULT_STORE_UNITS_1,
        DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_2 + DEFAULT_STORE_UNITS_3,
    ],
    "store_revision": "MAX",
    "units_in_file": DEFAULT_STORE_UNITS_1 + DEFAULT_STORE_UNITS_3,
}


def _setup_store_test(store, member, test):
    setup = test.get("setup", DEFAULT_STORE_TEST_SETUP)

    for units in setup:
        store_revision = store.get_max_unit_revision()
        print(f"setup store: {store_revision} {units}")
        update_store(store, store_revision=store_revision, units=units, user=member)
        for unit in store.units:
            comment = f"Set up unit({unit.source_f}) with store_revision: {store_revision}"
            _create_comment_on_unit(unit, member, comment)

    store_revision = test["store_revision"]
    units_before_update = list(store.unit_set.all().order_by("index"))

    if store_revision == "MAX":
        store_revision = store.get_max_unit_revision()

    elif store_revision == "MID":
        revisions = [unit.revision for unit in units_before_update]
        store_revision = sum(revisions) / len(revisions)

    return {
        "store": store,
        "units_in_file": test["units_in_file"],
        "store_revision": store_revision,
        "units_before_update": units_before_update,
    }


@pytest.fixture(params=UPDATE_STORE_TESTS.keys())
def store_diff_tests(request, tp0, member):
    from tests.factories import StoreDBFactory
    from pootle_store.diff import StoreDiff

    store = StoreDBFactory(translation_project=tp0, parent=tp0.directory)

    test = _setup_store_test(store, member, UPDATE_STORE_TESTS[request.param])
    test_store = create_store(units=test["units_in_file"])

    return {
        "diff": StoreDiff(test["store"], test_store, test["store_revision"]),
        "store": test["store"],
        "units_in_file": test["units_in_file"],
        "store_revision": test["store_revision"],
    }


@pytest.fixture(params=UPDATE_STORE_TESTS.keys())
def param_update_store_test(request, tp0, member, member2):
    from tests.factories import StoreDBFactory

    store = StoreDBFactory(translation_project=tp0, parent=tp0.directory)
    test = _setup_store_test(store, member, UPDATE_STORE_TESTS[request.param])
    update_store(
        test["store"],
        units=test["units_in_file"],
        store_revision=test["store_revision"],
        user=member2,
    )
    return test


def _require_store(tp, po_dir, name):
    """Helper to get/create a new store."""
    from pootle_store.constants import PARSED
    from pootle_store.models import Store

    parent_dir = tp.directory
    pootle_path = tp.pootle_path + name

    file_path = tp.real_path and os.path.join(po_dir, tp.real_path, name)

    try:
        store = Store.objects.get(pootle_path=pootle_path, translation_project=tp)
    except Store.DoesNotExist:
        store = Store.objects.create(
            file=file_path, parent=parent_dir, name=name, translation_project=tp,
        )
    if store.file.exists() and store.state < PARSED:
        store.update(store.file.store)

    return store


def _create_submission_and_suggestion(store, user, units=None, suggestion="SUGGESTION"):

    from pootle.core.models import Revision

    # Update store as user
    if units is None:
        units = [("Hello, world", "Hello, world UPDATED")]
    update_store(store, units, user=user, store_revision=Revision.get() + 1)

    # Add a suggestion
    unit = store.units[0]
    unit.add_suggestion(suggestion, user=user)
    return unit


def _create_comment_on_unit(unit, user, comment):
    from pootle_statistics.models import Submission, SubmissionFields, SubmissionTypes

    unit.translator_comment = comment
    unit.commented_on = timezone.now()
    unit.commented_by = user
    sub = Submission(
        creation_time=unit.commented_on,
        translation_project=unit.store.translation_project,
        submitter=user,
        unit=unit,
        store=unit.store,
        field=SubmissionFields.COMMENT,
        type=SubmissionTypes.NORMAL,
        new_value=comment,
    )
    sub.save()
    unit._comment_updated = True
    unit.save()


def _mark_unit_fuzzy(unit, user):
    from pootle_store.constants import FUZZY
    from pootle_statistics.models import Submission, SubmissionFields, SubmissionTypes

    sub = Submission(
        creation_time=unit.commented_on,
        translation_project=unit.store.translation_project,
        submitter=user,
        unit=unit,
        store=unit.store,
        field=SubmissionFields.STATE,
        type=SubmissionTypes.NORMAL,
        old_value=unit.state,
        new_value=FUZZY,
    )
    sub.save()
    unit.markfuzzy()
    unit._state_updated = True
    unit.save()


def _make_member_updates(store, member):
    # Member updates first unit, adding a suggestion, and marking unit as fuzzy
    _create_submission_and_suggestion(store, member)
    _create_comment_on_unit(store.units[0], member, "NICE COMMENT")
    _mark_unit_fuzzy(store.units[0], member)


@pytest.fixture
def af_tutorial_po(po_directory, settings, afrikaans_tutorial):
    """Require the /af/tutorial/tutorial.po store."""
    return _require_store(
        afrikaans_tutorial, settings.ZING_TRANSLATION_DIRECTORY, "tutorial.po"
    )


@pytest.fixture
def en_tutorial_po(po_directory, settings, english_tutorial):
    """Require the /en/tutorial/tutorial.po store."""
    return _require_store(
        english_tutorial, settings.ZING_TRANSLATION_DIRECTORY, "tutorial.po"
    )


@pytest.fixture
def en_tutorial_po_member_updated(po_directory, settings, english_tutorial, member):
    """Require the /en/tutorial/tutorial.po store."""
    store = _require_store(
        english_tutorial, settings.ZING_TRANSLATION_DIRECTORY, "tutorial.po"
    )
    _make_member_updates(store, member)
    return store


@pytest.fixture
def it_tutorial_po(po_directory, settings, italian_tutorial):
    """Require the /it/tutorial/tutorial.po store."""
    return _require_store(
        italian_tutorial, settings.ZING_TRANSLATION_DIRECTORY, "tutorial.po"
    )


@pytest.fixture
def issue_2401_po(po_directory, settings, afrikaans_tutorial):
    """Require the /af/tutorial/issue_2401.po store."""
    return _require_store(
        afrikaans_tutorial, settings.ZING_TRANSLATION_DIRECTORY, "issue_2401.po"
    )


@pytest.fixture
def store_po(tp0):
    """An empty Store in the /language0/project0 TP"""
    from pootle_translationproject.models import TranslationProject

    from tests.factories import StoreDBFactory

    tp = TranslationProject.objects.get(
        project__code="project0", language__code="language0"
    )

    return StoreDBFactory(
        parent=tp.directory, translation_project=tp, name="test_store.po"
    )


@pytest.fixture
def complex_po():
    from pootle_store.models import Store

    return Store.objects.get(name="complex.po")


@pytest.fixture
def diffable_stores(complex_po, request):
    from pootle_store.models import Store
    from pootle_translationproject.models import TranslationProject

    tp = TranslationProject.objects.get(
        language=complex_po.translation_project.language, project__code="project1"
    )
    other_po = Store.objects.create(
        name="complex.po",
        translation_project=tp,
        parent=tp.directory,
        pootle_path=complex_po.pootle_path.replace("project0", "project1"),
    )
    other_po.update(other_po.deserialize(complex_po.serialize()))

    return complex_po, other_po


@pytest.fixture
def dummy_store_structure_syncer():
    from pootle_store.syncer import StoreSyncer
    from django.utils.functional import cached_property

    class DummyUnit(object):
        def __init__(self, unit, expected):
            self.unit = unit
            self.expected = expected

        def convert(self, unit_class):
            assert unit_class == self.expected["unit_class"]
            return self.unit, unit_class



    class DummyDiskStore(object):
        def __init__(self, expected):
            self.expected = expected
            self.UnitClass = expected["unit_class"]

        @cached_property
        def _units(self):
            yield from self.expected["new_units"]

        def addunit(self, newunit):
            unit, unit_class = newunit
            assert unit == next(self._units).unit
            assert unit_class == self.UnitClass




    class DummyStoreSyncer(StoreSyncer):
        def __init__(self, *args, **kwargs):
            self.expected = kwargs.pop("expected")
            super().__init__(*args, **kwargs)

        @cached_property
        def disk_store(self):
            return DummyDiskStore(self.expected)

        @cached_property
        def _units(self):
            yield from self.expected["obsolete_units"]

        def obsolete_unit(self, unit, conservative):
            assert conservative == self.expected["conservative"]
            assert unit == next(self._units)
            return self.expected["obsolete_delete"]


    return DummyStoreSyncer, DummyUnit


@pytest.fixture
def dummy_store_syncer_units():
    from pootle_store.syncer import StoreSyncer
    from django.utils.functional import cached_property

    class DummyStore(object):
        def __init__(self, expected):
            self.expected = expected

        def findid_bulk(self, uids):
            return uids

    class DummyDiskStore(object):
        def __init__(self, expected):
            self.expected = expected

        def findid(self, uid):
            return self.expected["disk_ids"].get(uid)

    class DummyStoreSyncer(StoreSyncer):
        def __init__(self, *args, **kwargs):
            self.expected = kwargs.pop("expected")
            super().__init__(*args, **kwargs)
            self.store = DummyStore(self.expected)

        @property
        def dbid_index(self):
            return self.expected["db_ids"]

        @cached_property
        def disk_store(self):
            return DummyDiskStore(self.expected)

    return DummyStoreSyncer


@pytest.fixture
def dummy_store_syncer():
    from pootle_store.syncer import StoreSyncer
    from django.utils.functional import cached_property

    class DummyDiskStore(object):
        def __init__(self, expected):
            self.expected = expected

        def getids(self):
            return self.expected["disk_ids"]

    class DummyStoreSyncer(StoreSyncer):
        def __init__(self, *args, **kwargs):
            self.expected = kwargs.pop("expected")
            super().__init__(*args, **kwargs)

        @cached_property
        def disk_store(self):
            return DummyDiskStore(self.expected)

        @property
        def dbid_index(self):
            return self.expected["db_index"]

        def get_units_to_obsolete(self, old_ids_, new_ids_):
            return self.expected["obsolete_units"]

        def get_new_units(self, old_ids, new_ids):
            assert old_ids == set(self.expected["disk_ids"])
            assert new_ids == set(self.expected["db_index"].keys())
            return self.expected["new_units"]

        def get_common_units(self, units_, last_revision, conservative):
            assert last_revision == self.expected["last_revision"]
            assert conservative == self.expected["conservative"]
            return self.expected["common_units"]

        def update_structure(self, obsolete_units, new_units, conservative):
            assert obsolete_units == self.expected["obsolete_units"]
            assert new_units == self.expected["new_units"]
            assert conservative == self.expected["conservative"]
            return self.expected["structure_changed"]

        def sync_units(self, units):
            assert units == self.expected["common_units"]
            return self.expected["changes"]

    expected = dict(
        last_revision=23,
        conservative=True,
        update_structure=False,
        disk_ids=[5, 6, 7],
        db_index={"a": 1, "b": 2, "c": 3},
        structure_changed=(8, 9, 10),
        obsolete_units=["obsolete", "units"],
        new_units=["new", "units"],
        common_units=["common", "units"],
        changes=["some", "changes"],
    )
    return DummyStoreSyncer, expected


@pytest.fixture
def store0(tp0):
    return tp0.stores.get(name="store0.po")


@pytest.fixture
def ordered_po(test_fs, tp0):
    """Create a store with ordered units."""
    from tests.factories import StoreDBFactory

    store = StoreDBFactory(
        name="ordered.po", translation_project=tp0, parent=tp0.directory
    )
    with test_fs.open("data/po/ordered.po", "rb") as src:
        store.update(store.deserialize(src.read()))
    return store


@pytest.fixture
def numbered_po(test_fs, project0_disk):
    """Create a store with numbered units."""
    from tests.factories import (
        LanguageDBFactory,
        StoreDBFactory,
        TranslationProjectFactory,
    )

    tp = TranslationProjectFactory(project=project0_disk, language=LanguageDBFactory())
    store = StoreDBFactory(
        name="numbered.po", translation_project=tp, parent=tp.directory
    )
    with test_fs.open("data/po/1234.po", "rb") as src:
        store.update(store.deserialize(src.read()))
    return store


@pytest.fixture
def ordered_update_ttk(test_fs, store0):
    with test_fs.open("data/po/ordered_updated.po", "rb") as src:
        ttk = store0.deserialize(src.read())
    return ttk
