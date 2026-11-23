#!/usr/bin/env python3
"""Exercise maintenance package boundaries, provenance and integrity failures."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('package_dashboard',Path(__file__).with_name('package-dashboard.py'))
PACKAGE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class PackageChecks(unittest.TestCase):
    def setUp(self):
        self.private=tempfile.TemporaryDirectory()
        self.addCleanup(self.private.cleanup)
        self.base=Path(self.private.name)
        self.source=self.base/'source'
        self.source.mkdir()
        for name,body in {'version.py':"VERSION='fixture-1'\n",'run.sh':'#!/bin/sh\n',
                          'app.py':'# runtime\n','check_ui.py':'# diagnostic\n',
                          'verify_board.py':'# diagnostic\n','theme.json':'{"assets":[{"path":"fish.rig"}]}',
                          'fish.rig':'engine-specific asset\n',
                          'fixtures/theme-runtime/renderers/Fault.qml':'import QtQuick\nItem {}\n'}.items():
            path=self.source/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body)

    def test_runtime_excludes_checks_but_preserves_declared_assets(self):
        output=self.base/'runtime'
        PACKAGE.build(self.source,output)
        self.assertTrue((output/'fish.rig').is_file())
        self.assertFalse((output/'check_ui.py').exists())
        self.assertFalse((output/'verify_board.py').exists())
        self.assertFalse((output/'fixtures/theme-runtime/renderers').exists())
        (output/'verify_extra.py').write_text('# accidentally shipped\n')
        with self.assertRaisesRegex(ValueError,'diagnostici'):PACKAGE.verify(output)

    def test_diagnostic_package_retains_tools_and_fault_renderers(self):
        output=self.base/'diagnostic'
        PACKAGE.build(self.source,output,diagnostics=True)
        for name in ('check_ui.py','verify_board.py','fixtures/theme-runtime/renderers/Fault.qml'):
            self.assertTrue((output/name).is_file(),name)

    def test_baseline_limits_new_files_and_records_source(self):
        old=self.base/'old'
        PACKAGE.build(self.source,old,diagnostics=True)
        baseline=old/'release-manifest.json'
        (self.source/'unreleased.py').write_text('# deferred research\n')
        (self.source/'version.py').write_text("VERSION='fixture-2'\n")
        output=self.base/'maintenance'
        PACKAGE.build(self.source,output,baseline_manifest=baseline)
        self.assertFalse((output/'unreleased.py').exists())
        manifest=json.loads((output/'release-manifest.json').read_text())
        self.assertEqual(manifest['version'],'fixture-2')
        self.assertEqual(manifest['sourceBaseline']['version'],'fixture-1')
        self.assertEqual(manifest['sourceBaseline']['manifestSha256'],PACKAGE.digest(baseline))
        (output/'app.py').write_text('# corrupted\n')
        with self.assertRaisesRegex(ValueError,'Manifest differente'):PACKAGE.verify(output)

    def test_missing_baseline_file_fails_before_creating_output(self):
        old=self.base/'old'
        PACKAGE.build(self.source,old,diagnostics=True)
        (self.source/'app.py').unlink()
        output=self.base/'incomplete'
        with self.assertRaisesRegex(ValueError,'baseline mancanti'):
            PACKAGE.build(self.source,output,baseline_manifest=old/'release-manifest.json')
        self.assertFalse(output.exists())

    def test_explicit_native_addition_preserves_baseline_boundary(self):
        old=self.base/'old';PACKAGE.build(self.source,old)
        for name in ('egl_context_bridge.c','libsmartpc_egl_context_bridge.so','unreleased.py'):
            (self.source/name).write_text('fixture\n')
        output=self.base/'native-maintenance'
        PACKAGE.build(self.source,output,baseline_manifest=old/'release-manifest.json',
                      add_files=('egl_context_bridge.c','libsmartpc_egl_context_bridge.so'))
        manifest=json.loads((output/'release-manifest.json').read_text())
        self.assertEqual(['egl_context_bridge.c','libsmartpc_egl_context_bridge.so'],manifest['explicitAddedFiles'])
        self.assertFalse((output/'unreleased.py').exists())
        for invalid in ('../outside.py','/tmp/outside.py','missing.py'):
            with self.assertRaises(ValueError):
                PACKAGE.build(self.source,self.base/'invalid',baseline_manifest=old/'release-manifest.json',add_files=(invalid,))


if __name__=='__main__':unittest.main()
