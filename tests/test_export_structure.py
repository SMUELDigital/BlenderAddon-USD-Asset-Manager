import importlib.util
from pathlib import Path
import unittest
from pxr import Usd, UsdGeom, Gf
spec = importlib.util.spec_from_file_location('export_structure', Path(__file__).parents[1] / 'usd_stage_manager/export_structure.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ScopeTests(unittest.TestCase):
    def test_identity_removes_ops_and_preserves_child_world(self):
        s = Usd.Stage.CreateInMemory()
        root = UsdGeom.Xform.Define(s, '/World')
        root.AddTranslateOp().Set((5, 2, 1))
        group = UsdGeom.Xform.Define(s, '/World/geo')
        group.AddTransformOp().Set(Gf.Matrix4d(1))
        child = UsdGeom.Xform.Define(s, '/World/geo/object')
        child.AddTranslateOp().Set((1, 2, 3))
        before = child.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        self.assertEqual(m.make_scope(group.GetPrim()), '')
        self.assertEqual(group.GetPrim().GetTypeName(), 'Scope')
        self.assertEqual(before, child.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        self.assertFalse(group.GetPrim().HasProperty('xformOpOrder'))

    def test_samples_reset_and_translation_are_preserved(self):
        for mode in ('sample', 'reset', 'translate'):
            s = Usd.Stage.CreateInMemory()
            xf = UsdGeom.Xform.Define(s, '/group')
            if mode == 'sample': xf.AddTranslateOp().Set((0, 0, 0), 1)
            if mode == 'reset': xf.SetResetXformStack(True)
            if mode == 'translate': xf.AddTranslateOp().Set((0, 2, 0))
            before = s.GetRootLayer().ExportToString()
            self.assertTrue(m.make_scope(xf.GetPrim()))
            self.assertEqual(before, s.GetRootLayer().ExportToString())

    def test_mesh_is_not_retyped(self):
        s = Usd.Stage.CreateInMemory()
        p = UsdGeom.Mesh.Define(s, '/mesh').GetPrim()
        self.assertTrue(m.make_scope(p))
        self.assertEqual(p.GetTypeName(), 'Mesh')
