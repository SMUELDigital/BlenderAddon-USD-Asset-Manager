import importlib.util
from pathlib import Path
import tempfile
import shutil
import unittest
from pxr import Usd, UsdGeom, UsdShade, Sdf

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / 'usd_stage_manager' / file)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj
core = module('portable_core', 'core.py')
validation = module('stage_validation', 'validation.py')

class PortabilityTests(unittest.TestCase):
    def test_relative_save_does_not_change_working_layer(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'asset.usda'
            s = core.Session(); s.save(str(source))
            working = core.Session(str(source)); before = working.snapshot()
            out = Path(d) / 'shot.usda'; working.save(str(out))
            self.assertEqual(working.snapshot(), before)
            saved = Sdf.Layer.FindOrOpen(str(out))
            self.assertEqual(list(saved.subLayerPaths), ['asset.usda'])
            reopened = Usd.Stage.Open(str(out))
            self.assertTrue(reopened.GetPrimAtPath('/World'))

    def test_portable_dependency_relocation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'source'; source.mkdir()
            # Dependency resolution is independent of the asset byte format.
            asset = source / 'cache.bin'; asset.write_bytes(b'test asset')
            s = core.Session()
            p = s.stage.DefinePrim('/World/Data', 'Scope')
            p.CreateAttribute('userProperties:cache', Sdf.ValueTypeNames.Asset).Set(str(asset))
            output = s.publish_portable(str(root / 'publish'))
            self.assertFalse(Path(output).read_text().find(str(source)) >= 0)
            moved = root / 'moved'; shutil.move(str(root / 'publish'), moved)
            shutil.rmtree(source)
            reopened = Usd.Stage.Open(str(moved / 'stage.usda'))
            value = reopened.GetPrimAtPath('/World/Data').GetAttribute('userProperties:cache').Get()
            self.assertTrue(Path(value.resolvedPath).is_file())
            self.assertEqual(Path(value.resolvedPath).read_bytes(), b'test asset')

    def test_failed_publish_leaves_no_folder(self):
        with tempfile.TemporaryDirectory() as d:
            s = core.Session()
            s.stage.GetPrimAtPath('/World').CreateAttribute('missing', Sdf.ValueTypeNames.Asset).Set('/does/not/exist.exr')
            output = Path(d) / 'publish'
            with self.assertRaises(ValueError):
                s.publish_portable(str(output))
            self.assertFalse(output.exists())

    def test_official_validator_detects_bad_binding(self):
        s = core.Session()
        mesh = UsdGeom.Mesh.Define(s.stage, '/World/Mesh').GetPrim()
        mesh.CreateRelationship('material:binding').SetTargets(['/MissingMaterial'])
        report = validation.audit_stage(s.stage)
        self.assertFalse(report['passed'])
        self.assertTrue(report['validators'])

    def test_portable_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                core.Session().publish_portable(d)

if __name__ == '__main__': unittest.main()
