"""Run with blender --background --factory-startup --python tests/blender_smoke.py."""
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).parents[1]))
import bpy
import usd_stage_manager as addon
from pxr import Usd, UsdGeom

print('TEST Blender', bpy.app.version_string, 'USD', Usd.GetVersion())
addon.register()
ctx = bpy.context
assert bpy.ops.usdm.new() == {'FINISHED'}
assert len(ctx.scene.usdm.prims) == 1
assert bpy.ops.usdm.define(prim_path='/World/Group', prim_type='Xform') == {'FINISHED'}
assert len(ctx.scene.usdm.prims) == 2
assert bpy.ops.usdm.action(action='UNDO') == {'FINISHED'}
assert len(ctx.scene.usdm.prims) == 1
assert bpy.ops.usdm.action(action='REDO') == {'FINISHED'}
assert len(ctx.scene.usdm.prims) == 2
assert bpy.ops.usdm.clear(path='/World/Group') == {'FINISHED'}
assert len(ctx.scene.usdm.prims) == 1
# Organizing twice must not create cycles or disturb transforms.
bpy.ops.mesh.primitive_cube_add(location=(3, 4, 5))
obj = ctx.object
before = obj.matrix_world.copy()
assert bpy.ops.usdm.structure() == {'FINISHED'}
ctx.view_layer.update()
assert all(abs(before[r][c] - obj.matrix_world[r][c]) < 1e-6 for r in range(4) for c in range(4))
count = len(ctx.scene.objects)
assert bpy.ops.usdm.structure() == {'FINISHED'}
assert len(ctx.scene.objects) == count

with tempfile.TemporaryDirectory() as tmp:
    asset = os.path.join(tmp, 'asset.usda')
    stage = Usd.Stage.CreateNew(asset)
    root = UsdGeom.Xform.Define(stage, '/Asset').GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.Cube.Define(stage, '/Asset/Cube')
    stage.GetRootLayer().Save()
    assert bpy.ops.usdm.open(filepath=asset, replace_current=True) == {'FINISHED'}
    assert len(ctx.scene.usdm.prims) == 2
    ctx.scene.usdm.prim_index = 1
    assert ctx.scene.usdm.selected_path == '/Asset/Cube'
    ctx.scene.usdm.search = 'absent'
    assert ctx.scene.usdm.selected_path == ''
    ctx.scene.usdm.search = ''
    assert bpy.ops.usdm.preview() == {'FINISHED'}
    preview = ctx.scene.usdm.preview_collection
    assert preview is not None and len(preview.objects) > 0
    preview_count = len(preview.objects)
    # Refresh while a preview object is selected, a common interactive case.
    for o in ctx.selected_objects:
        o.select_set(False)
    selected = next(iter(preview.objects))
    selected.select_set(True)
    ctx.view_layer.objects.active = selected
    assert bpy.ops.usdm.preview() == {'FINISHED'}
    assert len(ctx.scene.usdm.preview_collection.objects) == preview_count
    assert bpy.ops.usdm.save(filepath=os.path.join(tmp, 'saved.usda')) == {'FINISHED'}
    assert bpy.ops.usdm.export_scene(filepath=os.path.join(tmp, 'blender.usdc')) == {'FINISHED'}
    assert Usd.Stage.Open(os.path.join(tmp, 'blender.usdc'))
    blend = os.path.join(tmp, 'test.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.wm.open_mainfile(filepath=blend)
    assert addon.session(bpy.context).prim('/Asset/Cube')
addon.unregister()
addon.register()
addon.unregister()
print('BLENDER_SMOKE_PASS')
