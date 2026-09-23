"""Export consistency, preview exclusion, portable publish and official validation."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
import bpy
import usd_stage_manager as addon
from usd_stage_manager.validation import audit_file
from pxr import Usd
addon.register()
bpy.ops.usdm.new()
bpy.ops.usdm.define(prim_path='/World/PreviewOnly', prim_type='Scope')
bpy.ops.usdm.preview()
cfg = bpy.context.scene.usdm
cfg.export_animation = False
cfg.export_selected = False
with tempfile.TemporaryDirectory() as tmp:
    output = str(Path(tmp)/'export.usdc')
    assert bpy.ops.usdm.export_scene(filepath=output) == {'FINISHED'}
    stage = Usd.Stage.Open(output)
    paths = [str(p.GetPath()) for p in stage.Traverse()]
    assert not any('PreviewOnly' in p for p in paths), paths
    assert any(p.GetTypeName() == 'Mesh' for p in stage.Traverse())
    assert [r['path'] for r in addon.session(bpy.context).rows()] == paths
    assert audit_file(output)['passed']
    assert bpy.ops.usdm.validate() == {'FINISHED'}
    assert bpy.ops.usdm.publish(filepath=str(Path(tmp)/'portable.usda')) == {'FINISHED'}
    assert audit_file(str(Path(tmp)/'portable/stage.usda'))['passed']
    assert bpy.ops.usdm.action(action='RESTORE_STAGE') == {'FINISHED'}
    assert addon.session(bpy.context).prim('/World/PreviewOnly')
print('EXPORT_PORTABILITY_PASS', bpy.app.version_string)
addon.unregister()
