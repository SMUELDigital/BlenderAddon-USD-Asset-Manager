bl_info = {
    "name": "USD Asset Manager",
    "author": "SMUELDigital",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "PROPERTIES",
    "description": "Export and import USD files with custom functions",
    "warning": "",
    "doc_url": "",
    "category": "Object"
}

import bpy
import os

class UsdExportButton(bpy.types.Operator):
    bl_idname = "scene.usd_export"
    bl_label = "Export USD"

    @classmethod
    def poll(cls, context):
        return context.scene.type == 'SCENE'

    def execute(self, context):
        scene = context.scene

        # Get the USD file path and other settings from the panel
        usd_file_path = bpy.path.abspath(scene.render.filepath) + ".usd"
        texture_folder = os.path.join(bpy.path.abspath(scene.render.filepath), "textures")

        # Set up the exporter
        bpy.ops.wm.usd_export(
            filepath=usd_file_path,
            export_selected_objects=True,
            use_tweak_mode=False,
            use_pass_through=False,
            use_render_layers=True,
            include_children=True,
            use_nodes=True,
            use_materials=True,
            use_textures=True,
            texture_folder=texture_folder
        )

        return {'FINISHED'}

    def _progress_callback(self, context, progress):
        # Update the progress bar
        pass

class UsdImportButton(bpy.types.Operator):
    bl_idname = "scene.usd_import"
    bl_label = "Import USD"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene

        # Get the USD file path and other settings from the panel
        usd_file_path = bpy.path.abspath(scene.render.filepath) + ".usd"

        # Set up the importer
        bpy.ops.wm.usd_import(
            filepath=usd_file_path,
            use_tweak_mode=False,
            use_pass_through=False,
            use_render_layers=True,
            include_children=True,
            use_nodes=True,
            use_materials=True,
            use_textures=True
        )

        return {'FINISHED'}

class USDManagerPanel(bpy.types.Panel):
    """Export and import USD files with custom functions"""
    bl_label = "USD Asset Manager"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # Different sizes in a row
        layout.label(text="USD Asset Manager:")
        row = layout.row(align=True)
        row.operator("scene.usd_export")
        row.operator("scene.usd_import")

        layout.label(text="Render Settings:")
        row = layout.row(align=True)
        row.operator("render.render")

def register():
    bpy.utils.register_class(USDManagerPanel)
    bpy.utils.register_class(UsdExportButton)
    bpy.utils.register_class(UsdImportButton)


def unregister():
    bpy.utils.unregister_class(USDManagerPanel)
    bpy.utils.unregister_class(UsdExportButton)
    bpy.utils.unregister_class(UsdImportButton)


if __name__ == "__main__":
    register()