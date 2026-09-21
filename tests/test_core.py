import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from pxr import Usd, UsdGeom, Sdf

spec = importlib.util.spec_from_file_location('stage_core', Path(__file__).parents[1] / 'usd_stage_manager/core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.asset = os.path.join(self.temp.name, 'asset.usda')
        stage = Usd.Stage.CreateNew(self.asset)
        root = UsdGeom.Xform.Define(stage, '/Asset').GetPrim()
        stage.SetDefaultPrim(root)
        UsdGeom.SetStageUpAxis(stage, 'Y')
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        UsdGeom.Cube.Define(stage, '/Asset/Cube')
        root.CreateAttribute('testStrength', Sdf.ValueTypeNames.Int).Set(1)
        variants = root.GetVariantSets().AddVariantSet('look')
        for name, size in [('small', 1.0), ('large', 3.0)]:
            variants.AddVariant(name)
            variants.SetVariantSelection(name)
            with variants.GetVariantEditContext():
                UsdGeom.Cube(stage.GetPrimAtPath('/Asset/Cube')).CreateSizeAttr(size)
        variants.SetVariantSelection('small')
        stage.GetRootLayer().Save()
        self.original = Path(self.asset).read_bytes()
        self.s = core.Session(self.asset)

    def test_source_protection_and_composed_save(self):
        self.s.set_visibility('/Asset/Cube', False)
        out = os.path.join(self.temp.name, 'shot.usda')
        self.s.save(out)
        restored = Usd.Stage.Open(out)
        self.assertEqual(UsdGeom.Imageable(restored.GetPrimAtPath('/Asset/Cube')).ComputeVisibility(), 'invisible')
        self.assertEqual(Path(self.asset).read_bytes(), self.original)
        with self.assertRaises(ValueError):
            self.s.save(self.asset)

    def test_metadata(self):
        self.assertEqual(UsdGeom.GetStageUpAxis(self.s.stage), 'Y')
        self.assertEqual(UsdGeom.GetStageMetersPerUnit(self.s.stage), 0.01)
        self.assertEqual(str(self.s.stage.GetDefaultPrim().GetPath()), '/Asset')

    def test_variants_and_history(self):
        self.s.set_variant('/Asset', 'look', 'large')
        self.assertEqual(self.s.prim('/Asset/Cube').GetAttribute('size').Get(), 3.0)
        self.s.undo()
        self.assertEqual(self.s.prim('/Asset/Cube').GetAttribute('size').Get(), 1.0)
        self.s.redo()
        self.assertEqual(self.s.prim('/Asset/Cube').GetAttribute('size').Get(), 3.0)
        self.assertEqual(Path(self.asset).read_bytes(), self.original)

    def test_search_and_inactive(self):
        self.assertEqual([r['path'] for r in self.s.rows('cube', ['/Asset'])], ['/Asset', '/Asset/Cube'])
        self.assertEqual([r['path'] for r in self.s.rows('', ['/Asset'])], ['/Asset'])
        self.s.set_active('/Asset/Cube', False)
        self.assertFalse(list(self.s.rows())[-1]['active'])

    def test_payload_and_persistence(self):
        s = core.Session()
        s.add_asset(self.asset, '/World/Ref', payload=True)
        self.assertTrue(s.prim('/World/Ref/Cube'))
        s.set_loaded('/World/Ref', False)
        restored = core.Session.from_snapshot(s.snapshot())
        self.assertFalse(restored.prim('/World/Ref').IsLoaded())
        restored.set_loaded('/World/Ref', True)
        self.assertTrue(restored.prim('/World/Ref/Cube'))

    def test_mute_restore_and_undo(self):
        self.s.mute_layer(self.asset)
        self.assertFalse(self.s.stage.GetPrimAtPath('/Asset'))
        self.s.define('/New')
        self.s.undo()  # restore while same layer remains muted
        self.assertTrue(self.s.stage.IsLayerMuted(self.asset))
        restored = core.Session.from_snapshot(self.s.snapshot())
        self.assertTrue(restored.stage.IsLayerMuted(self.asset))
        self.s.undo()
        self.assertTrue(self.s.prim('/Asset'))

    def test_validation_rollback(self):
        before = self.s.snapshot()
        for path in ('relative', '/', '/Bad Name', '/Asset.attr'):
            with self.assertRaises(ValueError):
                self.s.define(path)
        with self.assertRaises(ValueError):
            self.s.set_variant('/Asset', 'look', 'missing')
        self.assertEqual(self.s.snapshot(), before)

    def test_clear_and_scalar(self):
        self.s.set_scalar('/Asset/Cube', 'size', '8.5')
        self.assertEqual(self.s.prim('/Asset/Cube').GetAttribute('size').Get(), 8.5)
        self.s.clear_opinions('/Asset/Cube')
        self.assertEqual(self.s.prim('/Asset/Cube').GetAttribute('size').Get(), 1.0)

    def test_layer_strength_order_and_removal(self):
        override = os.path.join(self.temp.name, 'override.usda')
        stage = Usd.Stage.CreateNew(override)
        stage.OverridePrim('/Asset').CreateAttribute('testStrength', Sdf.ValueTypeNames.Int).Set(7)
        stage.GetRootLayer().Save()
        self.s.add_layer(override)
        self.assertEqual(self.s.prim('/Asset').GetAttribute('testStrength').Get(), 7)
        self.s.move_layer(0, 1)
        self.assertEqual(self.s.prim('/Asset').GetAttribute('testStrength').Get(), 1)
        self.s.remove_layer(0)
        self.assertEqual(self.s.prim('/Asset').GetAttribute('testStrength').Get(), 7)
        self.s.undo()
        self.assertEqual(self.s.prim('/Asset').GetAttribute('testStrength').Get(), 1)

    def test_flatten(self):
        self.s.set_variant('/Asset', 'look', 'large')
        out = os.path.join(self.temp.name, 'flat.usdc')
        self.s.save(out, flatten=True)
        flat = Usd.Stage.Open(out)
        self.assertEqual(flat.GetRootLayer().subLayerPaths, [])
        self.assertEqual(flat.GetPrimAtPath('/Asset/Cube').GetAttribute('size').Get(), 3)


if __name__ == '__main__':
    unittest.main()
