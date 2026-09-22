"""Scope typing follows role tags, not names; transformed groups stay Xforms."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
import bpy
import usd_stage_manager as addon
from pxr import Usd, UsdGeom
from usd_stage_manager.validation import audit_file
addon.register()
bpy.ops.usdm.new()
bpy.ops.usdm.structure()
roles = {o['usdm_structure']: o for o in bpy.context.scene.objects if o.get('usdm_structure')}
roles['geo'].name = 'Renamed Geometry'
ordinary = bpy.data.objects.new('geo', None)
bpy.context.scene.collection.objects.link(ordinary)
bpy.context.scene.usdm.export_animation = False
with tempfile.TemporaryDirectory() as tmp:
    out = str(Path(tmp) / 'scope.usdc')
    assert bpy.ops.usdm.export_scene(filepath=out) == {'FINISHED'}
    s = Usd.Stage.Open(out)
    scopes = [p for p in s.Traverse() if p.GetTypeName() == 'Scope' and p.GetName() != '_materials']
    assert len(scopes) == 4, [(str(p.GetPath()), p.GetTypeName()) for p in s.Traverse()]
    assert s.GetPrimAtPath('/World/geo').GetTypeName() == 'Xform'
    assert all(not p.HasProperty('xformOpOrder') for p in scopes)
    assert audit_file(out)['passed']
    roles['cameras'].location.x = 2
    native = str(Path(tmp) / 'native.usdc')
    assert bpy.ops.wm.usd_export(filepath=native, root_prim_path='/World') == {'FINISHED'}
    s = Usd.Stage.Open(native)
    p = s.GetPrimAtPath('/World/World/cameras')
    assert p.GetTypeName() == 'Xform'
    assert abs(UsdGeom.Xformable(p).GetLocalTransformation().ExtractTranslation()[0] - 2) < 1e-6
    assert s.GetPrimAtPath('/World/World/lights').GetTypeName() == 'Scope'
    assert addon.USDM_USDHook.warnings
print('SCOPE_EXPORT_PASS', bpy.app.version_string)
addon.unregister()
