#!/usr/bin/env python3
"""Development CLI forwarding checks; mocks do not prove runtime scene density."""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dense_dev', ROOT/'tools/dev.py')
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def arguments(scenario, **overrides):
    values = dict(scenario=scenario, units=None, ticks=3, seed=42, realtime=False,
                  connect=None, frames=30, screenshot=None, tactical=False, weather=None,
                  width=None, height=None, fov=None, sensitivity=None, port=7777, census=False)
    values.update(overrides)
    return SimpleNamespace(**values)


class DriverChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rh-dense-driver-')
        self.addCleanup(self.temp.cleanup)
        self.folder = pathlib.Path(self.temp.name)
        self.exe = self.folder/'frozen-revision'/'runtime'
        self.exe.parent.mkdir()
        self.calls = []
        self.reports = []
        self.battle_rows = []
        self.census_output = None
        for handle in (patch.object(dev, 'build', return_value=self.exe),
                       patch.object(dev, 'RUNS', self.folder/'runs'),
                       patch.object(dev, 'atomic', side_effect=lambda path, data: self.reports.append((path, data))),
                       patch.object(dev.subprocess, 'run', side_effect=self.run_mock),
                       patch.object(dev.shutil, 'which', return_value='/usr/bin/glxinfo'),
                       patch.dict(os.environ, {'DISPLAY': ':mock'}),
                       contextlib.redirect_stdout(io.StringIO())):
            handle.__enter__()
            self.addCleanup(handle.__exit__, None, None, None)

    def run_mock(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if cmd[0] == 'glxinfo':
            return subprocess.CompletedProcess(cmd, 0, 'Accelerated: yes\nOpenGL renderer string: mocked hardware\n', '')
        if '--screenshot' in cmd:
            pathlib.Path(cmd[cmd.index('--screenshot')+1]).write_bytes(b'P6\n1 1\n255\n\x01\x02\x03')
            output = json.dumps({'client_metrics': True, 'gpu_samples': 12})+'\n'
            output += ''.join(json.dumps(row)+'\n' for row in self.battle_rows)
        else:
            output = json.dumps({'submitted_entities': 8192, 'navigation': {'pending': 7}})
        if self.census_output is not None: output += '\n'+self.census_output+'\n'
        return subprocess.CompletedProcess(cmd, 0, output, '')

    def test_headless_dense_names_units_and_seed_forward(self):
        for scenario in ('scale-front', 'scale-hotspot'):
            dev.run_headless(arguments(scenario, units=16384, seed=19, realtime=True), True)
            cmd = self.calls[-1][0]
            self.assertEqual(cmd[cmd.index('--scenario')+1], scenario)
            self.assertEqual(cmd[cmd.index('--units')+1], '16384')
            self.assertEqual(cmd[cmd.index('--seed')+1], '19')
            self.assertIn('--realtime', cmd)
            report = self.reports[-1][1]
            self.assertEqual(report['scenario'], scenario)
            self.assertEqual(report['coverage']['navigation_backlog'], 7)
            self.assertEqual(report['coverage']['visible'], 0)
            self.assertIn('unmeasured', report['coverage']['network_bandwidth'])

    def test_headless_dense_below_baseline_rejected_before_build(self):
        for scenario in ('scale-front', 'scale-hotspot'):
            for units in (0, 2048, 8191):
                with self.assertRaisesRegex(RuntimeError, 'at least 8192'):
                    dev.run_headless(arguments(scenario, units=units))
        dev.build.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_headless_original_and_stretch_no_named_relabel(self):
        for scenario, expected in (('scale-open', 8192), ('scale-stretch', 16384)):
            dev.run_headless(arguments(scenario))
            cmd = self.calls[-1][0]
            self.assertNotIn('--scenario', cmd)
            self.assertEqual(cmd[cmd.index('--units')+1], str(expected))
            self.assertEqual(self.reports[-1][1]['scenario'], scenario)
        dev.run_headless(arguments('air-battle'))
        self.assertEqual(self.calls[-1][0][-2:], ['--scenario', 'air-battle'])

    def test_cli_run_dense_names_and_view_options_forward(self):
        for scenario in ('scale-front', 'scale-hotspot'):
            with patch.object(sys, 'argv', ['dev.py','run','--client','--scenario',scenario,
                                            '--width','1920','--height','1080','--weather','rain']):
                self.assertEqual(dev.main(), 0)
            cmd = self.calls[-1][0]
            self.assertEqual(cmd[cmd.index('--scenario')+1], scenario)
            self.assertEqual(cmd[cmd.index('--width')+1], '1920')
            self.assertEqual(cmd[cmd.index('--height')+1], '1080')
            self.assertEqual(cmd[cmd.index('--weather')+1], 'rain')

    def test_local_cohorts_cannot_connect_or_run_stretch(self):
        for scenario in dev.LOCAL_SCENARIOS:
            with patch.object(sys, 'argv', ['dev.py','run','--client','--scenario',scenario,'--connect','127.0.0.1']):
                with self.assertRaisesRegex(RuntimeError, 'local-only'):
                    dev.main()
        with patch.object(sys, 'argv', ['dev.py','run','--client','--scenario','scale-stretch']):
            with self.assertRaisesRegex(RuntimeError, 'Client scenarios'):
                dev.main()
        with patch.object(sys, 'argv', ['dev.py','run','--client','--scenario','scale-front','--units','16384']):
            with self.assertRaisesRegex(RuntimeError, 'fixed 8192'):
                dev.main()
        dev.build.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_scale_open_network_path_preserved(self):
        with patch.object(sys, 'argv', ['dev.py','run','--client','--connect','127.0.0.1','--port','7788']):
            self.assertEqual(dev.main(), 0)
        cmd = self.calls[-1][0]
        self.assertNotIn('--scenario', cmd)
        self.assertEqual(cmd[-4:], ['--connect','127.0.0.1','--port','7788'])

    def test_gpu_dense_reports_requested_scene_and_unmeasured_limits(self):
        for scenario in ('scale-front', 'scale-hotspot', 'air-battle'):
            dev.gpu_benchmark(arguments(scenario, width=1920, height=1080))
            cmd, kwargs = next(call for call in reversed(self.calls) if call[0][0] == str(self.exe))
            self.assertEqual(cmd[cmd.index('--scenario')+1], scenario)
            self.assertEqual(kwargs['env']['RH_AUDIO_DEVICE'], 'null')
            report = self.reports[-1][1]
            self.assertEqual(report['scenario'], 'local-solo-'+scenario)
            self.assertEqual(report['resolution'], [1920,1080])
            self.assertEqual(report['coverage']['visible_individual_count'], 'unmeasured')
            self.assertEqual(report['coverage']['detailed_counts'], 'final mesh telemetry only')
            self.assertIn('initial authored '+scenario, report['coverage']['camera'])
            self.assertIn('unverified', report['coverage']['audio_playback'])

    def test_gpu_battle_metrics_optional_single_row(self):
        dev.gpu_benchmark(arguments('scale-front'))
        self.assertNotIn('battle_metrics', self.reports[-1][1])
        self.battle_rows = [{'battle_metrics':True, 'projectiles_peak':42}]
        dev.gpu_benchmark(arguments('scale-front'))
        self.assertEqual(self.reports[-1][1]['battle_metrics'], self.battle_rows[0])
        self.battle_rows *= 2
        with self.assertRaisesRegex(RuntimeError, 'multiple battle_metrics'):
            dev.gpu_benchmark(arguments('scale-front'))

    def census_row(self, **changes):
        row=dict(visibility_census=True,width=1920,height=1080,visible_actors=1030,
                 visible_high=200,visible_low=800,visible_markers=30,
                 individually_detailed_actors=1000,source_tick=72,invalid_codes=0,
                 readback_reduce_ms=3.5)
        row.update(changes)
        return row

    def test_census_gpu_forwarding_and_exact_pixel_report(self):
        self.census_output=json.dumps(self.census_row())
        dev.gpu_benchmark(arguments('scale-hotspot',census=True,width=1920,height=1080))
        cmd=next(call[0] for call in reversed(self.calls) if call[0][0]==str(self.exe))
        self.assertIn('--census',cmd)
        report=self.reports[-1][1]
        self.assertEqual(report['visibility_census'],self.census_row())
        self.assertEqual(report['coverage']['visible_individual_count'],1030)
        self.assertEqual(report['coverage']['individually_detailed_actors'],1000)
        self.assertEqual(report['coverage']['detailed_counts'],dict(high=200,low=800,markers=30))
        self.assertIn('one frame, not peak',report['coverage']['visibility_scope'])
        self.assertIn('excluded',report['coverage']['census_timing_scope'])

    def test_census_bench_default_frames_bounded(self):
        self.census_output=json.dumps(self.census_row())
        dev.gpu_benchmark(arguments('scale-front',census=True,frames=None,width=1920,height=1080))
        cmd=next(call[0] for call in reversed(self.calls) if call[0][0]==str(self.exe))
        self.assertEqual(cmd[cmd.index('--frames')+1],'600')

    def test_census_run_forwards_and_checks_report(self):
        self.census_output=json.dumps(self.census_row())
        with patch.object(sys,'argv',['dev.py','run','--client','--census','--frames','30',
                                      '--width','1920','--height','1080']):
            self.assertEqual(dev.main(),0)
        self.assertIn('--census',self.calls[-1][0])
        self.assertTrue(self.calls[-1][1]['capture_output'])
        self.census_output=''
        with patch.object(sys,'argv',['dev.py','run','--client','--census','--frames','30']):
            with self.assertRaisesRegex(RuntimeError,'exactly one'):
                dev.main()

    def test_census_invalid_scope_and_unbounded_run_rejected_before_build(self):
        for argv in (['run','--census'],['server','--census'],['bench','--census'],
                     ['run','--client','--headless','--census','--frames','30'],
                     ['run','--client','--census'],['run','--client','--census','--frames','0'],
                     ['run','--client','--census','--frames','-1'],
                     ['run','--client','--census','--frames','10001']):
            with patch.object(sys,'argv',['dev.py',*argv]):
                with self.assertRaisesRegex(RuntimeError,'--census requires'):
                    dev.main()
        with self.assertRaisesRegex(RuntimeError,'--census requires --client'):
            dev.run_headless(arguments('scale-front',census=True))
        dev.build.assert_not_called()
        self.assertEqual(self.calls,[])

    def test_census_missing_malformed_duplicate_and_invalid_reports_rejected(self):
        args=arguments('scale-front',census=True,width=1920,height=1080)
        valid=json.dumps(self.census_row())
        for output in ('',valid+'\n'+valid,'{"visibility_census":',
                       valid.replace('"source_tick": 72','"source_tick": 72, "source_tick": 73'),
                       json.dumps(self.census_row(visibility_census=1))):
            with self.subTest(output=output):
                with self.assertRaises(RuntimeError): dev.visibility_report(output,args)
        bad_changes=[dict(width=1280),dict(height=True),dict(visible_actors=1031),
                     dict(visible_high=-1),dict(visible_low=1.5),dict(visible_markers=True),
                     dict(visible_actors=32769),dict(individually_detailed_actors=999),
                     dict(source_tick=-1),dict(source_tick=0x100000000),dict(source_tick=True),
                     dict(invalid_codes=1),dict(readback_reduce_ms=-1),
                     dict(readback_reduce_ms=float('nan')),dict(readback_reduce_ms=float('inf')),
                     dict(readback_reduce_ms='3.5')]
        for changes in bad_changes:
            with self.subTest(changes=changes):
                with self.assertRaises(RuntimeError):
                    dev.visibility_report(json.dumps(self.census_row(**changes)),args)
        for name in self.census_row():
            row=self.census_row(); del row[name]
            with self.subTest(missing=name):
                with self.assertRaises(RuntimeError): dev.visibility_report(json.dumps(row),args)

    def test_census_valid_empty_and_extra_context_preserved(self):
        args=arguments('scale-open',census=True,width=1920,height=1080)
        row=self.census_row(visible_actors=0,visible_high=0,visible_low=0,visible_markers=0,
                            individually_detailed_actors=0,source_tick=0,readback_reduce_ms=0,
                            renderer_context='fixture')
        # Formatting does not own validity; additional capture context is retained.
        output='unrelated telemetry\n'+json.dumps(row, separators=(', ', ': '))
        self.assertEqual(dev.visibility_report(output,args),row)

    def test_gpu_invalid_requests_rejected_before_build(self):
        for args in (arguments('scale-stretch'), arguments('scale-front', units=16384),
                     arguments('scale-hotspot', seed=1), arguments('scale-front', connect='127.0.0.1')):
            with self.assertRaises(RuntimeError):
                dev.gpu_benchmark(args)
        dev.build.assert_not_called()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DriverChecks)
    result = unittest.TextTestRunner().run(suite)
    print(json.dumps({'suite':'dense_driver','passed':result.wasSuccessful(),'cases':result.testsRun,
                      'scope':'mocked development forwarding and negative paths; no assembly runtime, GPU density, or physical audio proof'}))
    sys.exit(0 if result.wasSuccessful() else 1)
