import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parents[1]))
import bpy
import usd_stage_manager as a
a.register()
print('AREAS', [(x.type,x.x,x.y,x.width,x.height) for x in bpy.context.screen.areas])
windows_before=len(bpy.context.window_manager.windows)
area=next(x for x in bpy.context.screen.areas if x.type=='VIEW_3D')
with bpy.context.temp_override(area=area):
 print('RESULT',bpy.ops.usdm.window())
print('AFTER',[(x.type,x.x,x.y,x.width,x.height) for x in bpy.context.screen.areas])
print('DOCK',a.find_stage_dock(bpy.context.screen))
assert a.find_stage_dock(bpy.context.screen)
assert len(bpy.context.window_manager.windows)==windows_before
count=len(bpy.context.screen.areas)
with bpy.context.temp_override(area=next(x for x in bpy.context.screen.areas if x.type=='VIEW_3D')):
 assert bpy.ops.usdm.window()=={'FINISHED'}
assert len(bpy.context.screen.areas)==count
with tempfile.TemporaryDirectory() as tmp:
 path=str(Path(tmp)/'dock_test.blend')
 bpy.ops.wm.save_as_mainfile(filepath=path)
 bpy.ops.wm.open_mainfile(filepath=path,load_ui=True)
 assert a.find_stage_dock(bpy.context.screen)
print('DOCK_TEST_PASS')
