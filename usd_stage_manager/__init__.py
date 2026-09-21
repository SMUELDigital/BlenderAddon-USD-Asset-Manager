"""SMUELDigital USD Stage Manager — complete stage-oriented rewrite, 2026."""
bl_info = {
    'name': 'USD Stage Manager', 'author': 'SMUELDigital',
    'version': (2, 0, 1), 'blender': (5, 2, 0),
    'location': '3D View > Sidebar > USD Stage; Properties > Scene',
    'description': 'Solaris-inspired USD scene graph, composition layers and prim inspector',
    'category': 'Import-Export',
    'doc_url': 'https://github.com/SMUELDigital/BlenderAddon-USD-Asset-Manager',
}

import json
import hashlib
import os
import uuid
import bpy
from bpy.app.handlers import persistent
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       IntProperty, PointerProperty, StringProperty)
from bpy_extras.io_utils import ImportHelper, ExportHelper
from . import core

_SESSIONS = {}


def settings(context):
    return context.scene.usdm


def session(context):
    scene = context.scene
    key = scene.as_pointer()
    if key not in _SESSIONS:
        state = settings(context).snapshot
        _SESSIONS[key] = core.Session.from_snapshot(state) if state else core.Session()
    return _SESSIONS[key]


def persist(context):
    settings(context).snapshot = session(context).snapshot()


def redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def refresh(context):
    cfg = settings(context)
    s = session(context)
    selected = cfg.selected_path
    cfg.prims.clear()
    collapsed = json.loads(cfg.collapsed or '[]')
    for row in s.rows(cfg.search, collapsed):
        item = cfg.prims.add()
        for name, value in row.items():
            setattr(item, 'prim_type' if name == 'type' else name, value)
    index = next((i for i, p in enumerate(cfg.prims) if p.path == selected), -1)
    cfg.prim_index = index
    # A filtered-out selection must not remain an invisible editing target.
    if index < 0:
        cfg.selected_path = ''
    cfg.layers.clear()
    for path in s.root.subLayerPaths:
        item = cfg.layers.add()
        item.path = path
        item.name = os.path.basename(path)
        item.muted = s.stage.IsLayerMuted(path)
    cfg.layer_index = min(cfg.layer_index, len(cfg.layers) - 1)
    persist(context)
    redraw()


def search_update(self, context):
    if core.Usd:
        try:
            refresh(context)
        except Exception as exc:
            self.status = str(exc)


def selection_update(self, context):
    if 0 <= self.prim_index < len(self.prims):
        self.selected_path = self.prims[self.prim_index].path
    else:
        self.selected_path = ''


class USDM_Prim(bpy.types.PropertyGroup):
    path: StringProperty()
    depth: IntProperty()
    prim_type: StringProperty()
    active: BoolProperty()
    children: BoolProperty()
    payload: BoolProperty()
    loaded: BoolProperty()
    visible: BoolProperty()
    instance: BoolProperty()


class USDM_Layer(bpy.types.PropertyGroup):
    path: StringProperty()
    muted: BoolProperty()


class USDM_Settings(bpy.types.PropertyGroup):
    snapshot: StringProperty(options={'HIDDEN'})
    collapsed: StringProperty(default='[]', options={'HIDDEN'})
    search: StringProperty(name='Search prim path or type', update=search_update)
    prims: CollectionProperty(type=USDM_Prim)
    prim_index: IntProperty(default=-1, update=selection_update)
    selected_path: StringProperty()
    layers: CollectionProperty(type=USDM_Layer)
    layer_index: IntProperty(default=-1)
    status: StringProperty()
    inspect_frame: FloatProperty(name='USD Time', default=1.0)
    use_time: BoolProperty(name='Sample at USD Time', default=False)
    attr_search: StringProperty(name='Filter attributes')
    preview_collection: PointerProperty(type=bpy.types.Collection)
    preview_fingerprint: StringProperty(options={'HIDDEN'})
    export_animation: BoolProperty(name='Animation', default=True)
    export_selected: BoolProperty(name='Selected only', default=False)


class SafeOperator:
    """USD lives outside Blender's undo database; use the stage history buttons."""
    def execute(self, context):
        try:
            result = self.run(context)
            if result == {'CANCELLED'}:
                return result
            refresh(context)
            settings(context).status = ''
            return {'FINISHED'}
        except Exception as exc:
            settings(context).status = str(exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def find_stage_dock(screen):
    """Find the saved pane without depending on process-specific area pointers."""
    index = screen.usdm_dock_index
    areas = list(screen.areas)
    if 0 <= index < len(areas):
        area = areas[index]
        if area.type == 'PROPERTIES' and area.spaces.active.context == 'SCENE' and area.spaces.active.pin_id:
            return area
    return None


def configure_stage_dock(area, scene):
    area.type = 'PROPERTIES'
    space = area.spaces.active
    space.pin_id = scene
    space.context = 'SCENE'
    area.tag_redraw()


class USDM_OT_window(bpy.types.Operator):
    # Keep the operator ID for compatibility with saved shortcuts.
    bl_idname = 'usdm.window'
    bl_label = 'Open Embedded USD Stage'
    bl_description = 'Dock the USD stage below the viewport in this Blender window; reuse the existing pane'

    def execute(self, context):
        screen = context.screen
        dock = find_stage_dock(screen)
        if dock:
            configure_stage_dock(dock, context.scene)
        else:
            candidates = [a for a in screen.areas if a.type == 'VIEW_3D']
            viewport = context.area if context.area and context.area.type == 'VIEW_3D' else max(
                candidates, key=lambda a: a.width * a.height, default=None)
            if viewport is None:
                self.report({'ERROR'}, 'Open a 3D Viewport before docking the USD stage')
                return {'CANCELLED'}
            if viewport.height < 420:
                self.report({'ERROR'}, 'Enlarge the viewport vertically before opening the stage pane')
                return {'CANCELLED'}
            original = viewport.as_pointer()
            before = {a.as_pointer() for a in screen.areas}
            with context.temp_override(area=viewport):
                result = bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.40)
            if 'FINISHED' not in result:
                return {'CANCELLED'}
            pieces = [a for a in screen.areas if a.as_pointer() == original or a.as_pointer() not in before]
            dock = min(pieces, key=lambda a: a.y)
            configure_stage_dock(dock, context.scene)
            screen.usdm_dock_index = list(screen.areas).index(dock)
        if core.Usd:
            try:
                refresh(context)
            except Exception as exc:
                self.report({'WARNING'}, str(exc))
        return {'FINISHED'}


class USDM_OT_new(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.new'
    bl_label = 'New USD Stage'
    bl_description = 'Replace the current working stage; save it first if needed'

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        _SESSIONS[context.scene.as_pointer()] = core.Session()
        settings(context).collapsed = '[]'
        settings(context).selected_path = '/World'


class USDM_OT_open(SafeOperator, bpy.types.Operator, ImportHelper):
    bl_idname = 'usdm.open'
    bl_label = 'Open USD Stage'
    bl_description = 'Open as a source layer in a new working stage; save your current stage first'
    filename_ext = '.usd'
    filter_glob: StringProperty(default='*.usd;*.usda;*.usdc;*.usdz', options={'HIDDEN'})
    replace_current: BoolProperty(name='Replace current working stage', default=False)

    def draw(self, context):
        self.layout.label(text='Save the current stage before replacing it.')
        self.layout.prop(self, 'replace_current')

    def run(self, context):
        if settings(context).snapshot and not self.replace_current:
            raise ValueError('Enable Replace current working stage in the file browser')
        s = core.Session(bpy.path.abspath(self.filepath))
        _SESSIONS[context.scene.as_pointer()] = s
        settings(context).collapsed = '[]'
        settings(context).selected_path = ''


class USDM_OT_save(SafeOperator, bpy.types.Operator, ExportHelper):
    bl_idname = 'usdm.save'
    bl_label = 'Save USD Stage As'
    filename_ext = '.usda'
    filter_glob: StringProperty(default='*.usd;*.usda;*.usdc', options={'HIDDEN'})
    flatten: BoolProperty(name='Flatten composition', default=False,
                          description='Bake composed prims into one layer; variants and composition arcs are lost')

    def run(self, context):
        session(context).save(bpy.path.abspath(self.filepath), self.flatten)
        self.report({'INFO'}, 'USD stage saved')


class USDM_OT_action(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.action'
    bl_label = 'USD Stage Action'
    bl_description = 'Edit the USD working layer (use USD Undo to reverse)'
    action: StringProperty()
    path: StringProperty()
    index: IntProperty(default=-1)

    def run(self, context):
        s, cfg = session(context), settings(context)
        path = self.path or cfg.selected_path
        if self.action == 'REFRESH':
            return
        if self.action == 'UNDO':
            s.undo()
        elif self.action == 'REDO':
            s.redo()
        elif self.action == 'COLLAPSE':
            collapsed = set(json.loads(cfg.collapsed))
            collapsed.symmetric_difference_update([path])
            cfg.collapsed = json.dumps(sorted(collapsed))
        elif self.action == 'EXPAND_ALL':
            cfg.collapsed = '[]'
        elif self.action == 'COLLAPSE_ALL':
            cfg.collapsed = json.dumps([r['path'] for r in s.rows() if r['children']])
        elif self.action == 'VISIBILITY':
            imageable = core.UsdGeom.Imageable(s.prim(path))
            if not imageable:
                raise ValueError('This prim is not imageable')
            s.set_visibility(path, imageable.ComputeVisibility() == core.UsdGeom.Tokens.invisible)
        elif self.action == 'ACTIVE':
            s.set_active(path, not s.prim(path).IsActive())
        elif self.action == 'PAYLOAD':
            s.set_loaded(path, not s.prim(path).IsLoaded())
        elif self.action == 'MUTE':
            s.mute_layer(path)
        elif self.action == 'LAYER_UP':
            s.move_layer(cfg.layer_index, -1)
            cfg.layer_index = max(0, cfg.layer_index - 1)
        elif self.action == 'LAYER_DOWN':
            s.move_layer(cfg.layer_index, 1)
            cfg.layer_index = min(len(cfg.layers) - 1, cfg.layer_index + 1)
        elif self.action == 'LAYER_REMOVE':
            if cfg.layer_index < 0:
                raise ValueError('Select a source layer')
            s.remove_layer(cfg.layer_index)
        elif self.action == 'DEFAULT':
            s.set_default(path)
        elif self.action == 'CLEAR':
            s.clear_opinions(path)
        else:
            raise ValueError('Unknown stage action')


class USDM_OT_clear(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.clear'
    bl_label = 'Clear Working Opinions for Subtree'
    bl_description = 'Remove working-layer edits on the selected prim and descendants; source opinions remain'
    path: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        session(context).clear_opinions(self.path or settings(context).selected_path)


class USDM_OT_add_layer(SafeOperator, bpy.types.Operator, ImportHelper):
    bl_idname = 'usdm.add_layer'
    bl_label = 'Add USD Sublayer'
    filter_glob: StringProperty(default='*.usd;*.usda;*.usdc', options={'HIDDEN'})

    def run(self, context):
        session(context).add_layer(bpy.path.abspath(self.filepath))


class USDM_OT_add_asset(SafeOperator, bpy.types.Operator, ImportHelper):
    bl_idname = 'usdm.add_asset'
    bl_label = 'Reference USD Asset'
    filter_glob: StringProperty(default='*.usd;*.usda;*.usdc;*.usdz', options={'HIDDEN'})
    prim_path: StringProperty(name='New prim path', default='/World/Asset')
    payload: BoolProperty(name='Use payload', default=False)

    def run(self, context):
        session(context).add_asset(bpy.path.abspath(self.filepath), self.prim_path, self.payload)
        settings(context).selected_path = self.prim_path


class USDM_OT_define(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.define'
    bl_label = 'Create USD Prim'
    prim_path: StringProperty(name='Prim path', default='/World/NewPrim')
    prim_type: EnumProperty(name='Type', items=[('Xform', 'Xform', ''), ('Scope', 'Scope', '')])

    def invoke(self, context, event):
        self.prim_path = (settings(context).selected_path or '/World') + '/NewPrim'
        return context.window_manager.invoke_props_dialog(self)

    def run(self, context):
        session(context).define(self.prim_path, self.prim_type)
        settings(context).selected_path = self.prim_path


class USDM_OT_variant(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.variant'
    bl_label = 'Choose USD Variant'
    variant_set: StringProperty()
    prim_path: StringProperty()
    value: StringProperty()

    def invoke(self, context, event):
        p = session(context).prim(self.prim_path)
        values = p.GetVariantSet(self.variant_set).GetVariantNames()
        path, name = self.prim_path, self.variant_set
        def draw(menu, ctx):
            menu.layout.operator_context = 'EXEC_DEFAULT'
            for value in values:
                op = menu.layout.operator('usdm.variant', text=value)
                op.prim_path, op.variant_set, op.value = path, name, value
        context.window_manager.popup_menu(draw, title=self.variant_set)
        return {'FINISHED'}

    def run(self, context):
        session(context).set_variant(self.prim_path, self.variant_set, self.value)


class USDM_OT_purpose(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.purpose'
    bl_label = 'Set USD Purpose'
    value: EnumProperty(name='Purpose', items=[(v, v.title(), '') for v in ('default', 'render', 'proxy', 'guide')])

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def run(self, context):
        session(context).set_purpose(settings(context).selected_path, self.value)


class USDM_OT_attribute(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.attribute'
    bl_label = 'Edit Default Attribute Value'
    bl_description = 'Author a default value; existing animation samples take precedence at sampled times'
    attribute: StringProperty(name='Attribute')
    prim_path: StringProperty()
    value: StringProperty(name='Value')

    def invoke(self, context, event):
        a = session(context).prim(self.prim_path).GetAttribute(self.attribute)
        self.value = str(a.Get())
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        self.layout.label(text=self.attribute)
        self.layout.prop(self, 'value')
        self.layout.label(text='Authors the default value, not a time sample.')

    def run(self, context):
        session(context).set_scalar(self.prim_path, self.attribute, self.value)


def supported_kwargs(operator, values):
    available = operator.get_rna_type().properties.keys()
    return {key: value for key, value in values.items() if key in available}


class USDM_OT_preview(SafeOperator, bpy.types.Operator):
    bl_idname = 'usdm.preview'
    bl_label = 'Build / Refresh Viewport Preview'
    bl_description = 'Import a flattened stage into a managed collection; replaces only the previous preview'

    def run(self, context):
        if context.mode != 'OBJECT':
            raise ValueError('Switch to Object Mode first')
        cfg, s = settings(context), session(context)
        # Persistent cache: Blender may read animation/volume data after a .blend reopens.
        directory = bpy.utils.user_resource('DATAFILES', path='usd_stage_manager/cache', create=True)
        path = os.path.join(directory, uuid.uuid4().hex + '.usdc')
        s.save(path, flatten=True)
        old_objects = set(bpy.data.objects)
        selected = list(context.selected_objects)
        active = context.view_layer.objects.active
        old_layer = context.view_layer.active_layer_collection
        context.view_layer.active_layer_collection = context.view_layer.layer_collection
        try:
            kwargs = supported_kwargs(bpy.ops.wm.usd_import, {'filepath': path, 'set_frame_range': False,
                         'import_usd_preview': True, 'import_visible_only': True})
            result = bpy.ops.wm.usd_import(**kwargs)
            if 'FINISHED' not in result:
                raise RuntimeError('Blender USD import did not finish')
            imported = set(bpy.data.objects) - old_objects
            collection = bpy.data.collections.new('USD Stage Preview')
            collection['usdm_preview'] = True
            context.scene.collection.children.link(collection)
            for obj in imported:
                collection.objects.link(obj)
                for owner in list(obj.users_collection):
                    if owner != collection:
                        owner.objects.unlink(obj)
            old = cfg.preview_collection
            if old and old.get('usdm_preview'):
                for obj in list(old.objects):
                    # User-linked objects outside the managed collection are preserved.
                    if len(obj.users_collection) == 1:
                        bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(old)
            cfg.preview_collection = collection
            cfg.preview_fingerprint = hashlib.sha256(s.snapshot().encode()).hexdigest()
        except Exception:
            for obj in set(bpy.data.objects) - old_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            raise
        finally:
            try:
                context.view_layer.active_layer_collection = old_layer
            except (ReferenceError, TypeError):
                context.view_layer.active_layer_collection = context.view_layer.layer_collection
            for obj in context.selected_objects:
                obj.select_set(False)
            for obj in selected:
                try:
                    if obj.name in context.view_layer.objects:
                        obj.select_set(True)
                except ReferenceError:
                    pass  # Previous preview object was intentionally replaced.
            try:
                if active and active.name in context.view_layer.objects:
                    context.view_layer.objects.active = active
            except ReferenceError:
                pass


class USDM_OT_export_scene(bpy.types.Operator, ExportHelper):
    bl_idname = 'usdm.export_scene'
    bl_label = 'Export Blender Scene to USD'
    filename_ext = '.usdc'
    filter_glob: StringProperty(default='*.usd;*.usda;*.usdc', options={'HIDDEN'})

    def execute(self, context):
        try:
            cfg = settings(context)
            path = bpy.path.abspath(self.filepath)
            if core.Usd and context.scene.as_pointer() in _SESSIONS:
                s = session(context)
                sources = {os.path.realpath(x.realPath) for x in s.stage.GetUsedLayers() if x.realPath}
                sources.update(os.path.realpath(x) for x in s.root.subLayerPaths)
                if os.path.realpath(path) in sources:
                    raise ValueError('Choose a new filename; this is a source layer in the open stage')
            kwargs = supported_kwargs(bpy.ops.wm.usd_export, {
                'filepath': path, 'selected_objects_only': cfg.export_selected,
                'export_animation': cfg.export_animation, 'export_materials': True,
                'root_prim_path': '/World', 'relative_paths': True})
            return bpy.ops.wm.usd_export(**kwargs)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class USDM_OT_structure(bpy.types.Operator):
    bl_idname = 'usdm.structure'
    bl_label = 'Organize Blender Scene for USD'
    bl_description = 'Create World/geo/lights/cameras/extras empties, preserving existing parenting and world transforms'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, 'Switch to Object Mode first')
            return {'CANCELLED'}
        roots = [o for o in context.scene.objects if o.parent is None and not o.get('usdm_structure')
                 and o.library is None and not any(c.get('usdm_preview') for c in o.users_collection)]
        # Reuse only explicitly tagged empties; do not adopt user objects by name.
        def empty(role, parent=None):
            obj = next((o for o in context.scene.objects if o.get('usdm_structure') == role), None)
            if obj is None:
                obj = bpy.data.objects.new(role, None)
                obj['usdm_structure'] = role
                context.scene.collection.objects.link(obj)
                obj.parent = parent
            return obj
        root = empty('World')
        groups = {n: empty(n, root) for n in ('geo', 'lights', 'cameras', 'extras')}
        for obj in roots:
            matrix = obj.matrix_world.copy()
            category = {'MESH': 'geo', 'CURVE': 'geo', 'CURVES': 'geo', 'VOLUME': 'geo',
                        'LIGHT': 'lights', 'CAMERA': 'cameras'}.get(obj.type, 'extras')
            obj.parent = groups[category]
            obj.matrix_world = matrix
        return {'FINISHED'}


def action_button(layout, text, action, icon='NONE', path=''):
    op = layout.operator('usdm.action', text=text, icon=icon)
    op.action, op.path = action, path
    return op


class USDM_UL_prims(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.depth:
            indent = row.row()
            indent.ui_units_x = min(item.depth, 12) * 0.7
            indent.label(text='')
        collapsed = set(json.loads(data.collapsed or '[]'))
        if item.children:
            action_button(row, '', 'COLLAPSE', 'TRIA_RIGHT' if item.path in collapsed else 'TRIA_DOWN', item.path)
        else:
            row.label(text='', icon='BLANK1')
        cell = row.row()
        cell.enabled = item.active
        cell.label(text=item.name, icon={'Mesh': 'MESH_DATA', 'Xform': 'EMPTY_AXIS',
                        'Camera': 'CAMERA_DATA', 'Material': 'MATERIAL', 'Scope': 'OUTLINER_COLLECTION'}.get(item.prim_type, 'OBJECT_DATA'))
        row.label(text=item.prim_type)
        if item.instance:
            row.label(text='', icon='LINKED')
        if item.payload:
            action_button(row, '', 'PAYLOAD', 'PACKAGE' if item.loaded else 'IMPORT', item.path)
        action_button(row, '', 'VISIBILITY', 'HIDE_OFF' if item.visible else 'HIDE_ON', item.path)
        action_button(row, '', 'ACTIVE', 'CHECKBOX_HLT' if item.active else 'CHECKBOX_DEHLT', item.path)


class USDM_UL_layers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text=item.name, icon='FILE')
        action_button(row, '', 'MUTE', 'HIDE_ON' if item.muted else 'HIDE_OFF', item.path)


class StagePanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'


class USDM_PT_stage(StagePanel, bpy.types.Panel):
    bl_label = 'USD Stage Manager'
    bl_idname = 'USDM_PT_stage'
    bl_order = -100

    def draw(self, context):
        layout, cfg = self.layout, settings(context)
        if not core.Usd:
            layout.label(text='OpenUSD Python support is missing in this Blender build.', icon='ERROR')
            layout.label(text=core.USD_ERROR)
            layout.operator('wm.usd_import', text='Native USD Import')
            layout.operator('usdm.export_scene')
            return
        row = layout.row(align=True)
        row.operator('usdm.new', text='New', icon='FILE_NEW')
        row.operator('usdm.open', text='Open', icon='FILE_FOLDER')
        row.operator('usdm.save', text='Save As', icon='FILE_TICK')
        action_button(row, '', 'REFRESH', 'FILE_REFRESH')
        row = layout.row(align=True)
        action_button(row, 'Undo USD', 'UNDO', 'LOOP_BACK')
        action_button(row, 'Redo USD', 'REDO', 'LOOP_FORWARDS')
        layout.operator('usdm.preview', text='Refresh Viewport', icon='SHADING_RENDERED')
        if cfg.status:
            layout.label(text=cfg.status[:150], icon='ERROR')
        layout.label(text='Edit target: Working Layer • source files protected', icon='LOCKED')
        key = context.scene.as_pointer()
        if key in _SESSIONS and cfg.preview_collection and cfg.preview_fingerprint != hashlib.sha256(cfg.snapshot.encode()).hexdigest():
            layout.label(text='Stage changed — refresh viewport preview', icon='INFO')
        if not cfg.snapshot:
            layout.label(text='Choose New or Open to start.')
            return
        row = layout.row(align=True)
        row.prop(cfg, 'search', text='', icon='VIEWZOOM')
        action_button(row, '', 'EXPAND_ALL', 'ADD')
        action_button(row, '', 'COLLAPSE_ALL', 'REMOVE')
        layout.template_list('USDM_UL_prims', '', cfg, 'prims', cfg, 'prim_index', rows=15)
        row = layout.row(align=True)
        row.operator('usdm.define', text='New Prim', icon='ADD')
        row.operator('usdm.add_asset', text='Reference / Payload', icon='LINKED')
        layout.label(text=cfg.selected_path or 'Select a prim')


class USDM_PT_layers(StagePanel, bpy.types.Panel):
    bl_label = 'USD Layer Stack'
    bl_parent_id = 'USDM_PT_stage'

    @classmethod
    def poll(cls, context):
        return bool(core.Usd and settings(context).snapshot)

    def draw(self, context):
        layout, cfg = self.layout, settings(context)
        layout.label(text='Strongest → weakest; working layer always strongest')
        row = layout.row()
        row.template_list('USDM_UL_layers', '', cfg, 'layers', cfg, 'layer_index', rows=4)
        col = row.column(align=True)
        col.operator('usdm.add_layer', text='', icon='ADD')
        action_button(col, '', 'LAYER_REMOVE', 'REMOVE')
        action_button(col, '', 'LAYER_UP', 'TRIA_UP')
        action_button(col, '', 'LAYER_DOWN', 'TRIA_DOWN')
        if 0 <= cfg.layer_index < len(cfg.layers):
            layout.label(text=cfg.layers[cfg.layer_index].path)
        layout.label(text='Nested sublayers and references appear in Prim Composition below.')


class USDM_PT_inspector(StagePanel, bpy.types.Panel):
    bl_label = 'USD Prim Inspector'
    bl_parent_id = 'USDM_PT_stage'

    @classmethod
    def poll(cls, context):
        return bool(core.Usd and settings(context).selected_path)

    def draw(self, context):
        layout, cfg = self.layout, settings(context)
        try:
            s = session(context)
            p = s.prim(cfg.selected_path)
            data = s.inspect(cfg.selected_path, cfg.inspect_frame if cfg.use_time else None)
        except Exception as exc:
            layout.label(text=str(exc))
            return
        row = layout.row(align=True)
        row.label(text=p.GetTypeName() or 'Untyped', icon='OBJECT_DATA')
        action_button(row, 'Set Default Prim', 'DEFAULT')
        row.operator('usdm.purpose', text='Purpose')
        layout.operator('usdm.clear', icon='LOOP_BACK')
        for name, current, choices in data['variants']:
            row = layout.row()
            row.label(text=name)
            row.operator_context = 'INVOKE_DEFAULT'
            op = row.operator('usdm.variant', text=current or 'Choose Variant', icon='DOWNARROW_HLT')
            op.prim_path, op.variant_set = cfg.selected_path, name
        row = layout.row()
        row.prop(cfg, 'use_time')
        sub = row.row()
        sub.enabled = cfg.use_time
        sub.prop(cfg, 'inspect_frame')
        layout.prop(cfg, 'attr_search', text='', icon='VIEWZOOM')
        box = layout.box()
        for name, kind, value, samples in data['attributes']:
            if cfg.attr_search.casefold() not in name.casefold():
                continue
            row = box.row(align=True)
            row.label(text=name + (' [animated]' if samples else ''))
            row.label(text=value)
            if kind in ('string', 'token', 'bool', 'int', 'int64', 'uint', 'uint64', 'float', 'double', 'half'):
                op = row.operator('usdm.attribute', text='', icon='GREASEPENCIL')
                op.attribute, op.prim_path = name, cfg.selected_path
        for name, target in data['relationships']:
            if target:
                layout.label(text=name + ' → ' + target)
        box = layout.box()
        box.label(text='Prim Composition (strongest first)', icon='LINENUMBERS_ON')
        for source, path in data['stack']:
            box.label(text=os.path.basename(source) + ': ' + path)


class USDM_PT_bridge(StagePanel, bpy.types.Panel):
    bl_label = 'Blender Scene ↔ USD'
    bl_parent_id = 'USDM_PT_stage'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout, cfg = self.layout, settings(context)
        layout.operator('usdm.structure')
        row = layout.row()
        row.prop(cfg, 'export_animation')
        row.prop(cfg, 'export_selected')
        layout.operator('usdm.export_scene')
        layout.operator('wm.usd_import', text='Import USD as Editable Blender Objects')
        layout.label(text='Preview is a snapshot. Blender edits do not write back to the USD stage.')


class USDM_PT_sidebar(bpy.types.Panel):
    bl_label = 'USD Stage'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'USD Stage'

    def draw(self, context):
        layout = self.layout
        layout.operator('usdm.window', icon='WINDOW')
        row = layout.row(align=True)
        row.operator('usdm.new', text='New')
        row.operator('usdm.open', text='Open')
        layout.operator('usdm.preview')
        layout.operator('usdm.save')
        layout.separator()
        layout.operator('usdm.export_scene')


@persistent
def load_post(_):
    _SESSIONS.clear()
    # Persisted tree rows remain available; sessions are restored lazily from the .blend snapshot.


@persistent
def undo_post(_):
    # Blender Undo may roll back the stored snapshot or scene copies. Do not retain stale USD state.
    _SESSIONS.clear()


CLASSES = (USDM_Prim, USDM_Layer, USDM_Settings, USDM_OT_window, USDM_OT_new, USDM_OT_open,
           USDM_OT_save, USDM_OT_action, USDM_OT_clear, USDM_OT_add_layer, USDM_OT_add_asset,
           USDM_OT_define, USDM_OT_variant, USDM_OT_purpose, USDM_OT_attribute, USDM_OT_preview,
           USDM_OT_export_scene, USDM_OT_structure, USDM_UL_prims, USDM_UL_layers,
           USDM_PT_stage, USDM_PT_layers, USDM_PT_inspector, USDM_PT_bridge, USDM_PT_sidebar)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.usdm = PointerProperty(type=USDM_Settings)
    bpy.types.Screen.usdm_dock_index = IntProperty(default=-1, options={'HIDDEN'})
    for handlers, fn in ((bpy.app.handlers.load_post, load_post), (bpy.app.handlers.undo_post, undo_post),
                         (bpy.app.handlers.redo_post, undo_post)):
        if fn not in handlers:
            handlers.append(fn)


def unregister():
    for handlers, fn in ((bpy.app.handlers.load_post, load_post), (bpy.app.handlers.undo_post, undo_post),
                         (bpy.app.handlers.redo_post, undo_post)):
        if fn in handlers:
            handlers.remove(fn)
    del bpy.types.Screen.usdm_dock_index
    del bpy.types.Scene.usdm
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _SESSIONS.clear()
    # Persistent preview files may be used by saved .blend files; never delete them here.


if __name__ == '__main__':
    register()
