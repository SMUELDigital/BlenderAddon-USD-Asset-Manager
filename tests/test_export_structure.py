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

class OrganizationTests(unittest.TestCase):
    def test_material_binding_and_light_paths(self):
        from pxr import UsdShade, UsdLux, Sdf
        s = Usd.Stage.CreateInMemory()
        world = UsdGeom.Xform.Define(s, '/World/World').GetPrim()
        UsdGeom.Xform.Define(s, '/World')
        UsdGeom.Scope.Define(s, '/World/_materials')
        mat = UsdShade.Material.Define(s, '/World/_materials/Mat')
        shader = UsdShade.Shader.Define(s, '/World/_materials/Mat/Shader')
        shader.CreateIdAttr('UsdPreviewSurface')
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        mesh = UsdGeom.Mesh.Define(s, '/World/World/geo/Mesh').GetPrim()
        UsdShade.MaterialBindingAPI.Apply(mesh).Bind(mat)
        UsdLux.DomeLight.Define(s, '/World/env_light')
        m.organize_export(s, world.GetPath(), {})
        self.assertEqual(world.GetTypeName(), 'Xform')
        self.assertEqual(Usd.ModelAPI(world).GetKind(), 'assembly')
        self.assertTrue(world.IsModel())
        self.assertTrue(s.GetPrimAtPath('/World/World/lights/env_light'))
        self.assertFalse(s.GetPrimAtPath('/World/env_light'))
        self.assertFalse(s.GetPrimAtPath('/World/_materials'))
        bound = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial()[0]
        self.assertEqual(str(bound.GetPath()), '/World/World/materials/Mat')
        out = bound.GetSurfaceOutput().GetConnectedSource()
        self.assertEqual(str(out[0].GetPath()), '/World/World/materials/Mat/Shader')

    def test_animated_light_world_transform_and_collision(self):
        from pxr import UsdLux
        s = Usd.Stage.CreateInMemory()
        world = UsdGeom.Xform.Define(s, '/World')
        world.AddRotateZOp().Set(30)
        UsdGeom.Scope.Define(s, '/World/lights')
        UsdLux.DomeLight.Define(s, '/World/lights/Light')
        parent = UsdGeom.Xform.Define(s, '/Rig')
        op = parent.AddRotateYOp(); op.Set(0, 1); op.Set(90, 2)
        light = UsdLux.SphereLight.Define(s, '/Rig/Light')
        UsdGeom.Xformable(light).AddTranslateOp().Set((1, 2, 3))
        times = (1, 1.25, 1.5, 2)
        before = [UsdGeom.XformCache(t).GetLocalToWorldTransform(light.GetPrim()) for t in times]
        m.organize_export(s, world.GetPath(), {})
        moved = [p for p in s.Traverse() if p.GetTypeName() == 'SphereLight'][0]
        self.assertTrue(str(moved.GetPath()).startswith('/World/lights/'))
        self.assertTrue(s.GetPrimAtPath('/World/lights/Light'))
        for t, expected in zip(times, before):
            self.assertTrue(Gf.IsClose(expected, UsdGeom.XformCache(t).GetLocalToWorldTransform(moved), 1e-10))
