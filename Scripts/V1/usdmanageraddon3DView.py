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
# Function to create directory if it doesn't exist
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Function to export geometry as USD
def export_geometry(output_path):
    bpy.ops.wm.usd_export(filepath=output_path, selected_objects_only=True, export_materials=False)

# Function to export materials as USD
def export_materials(output_path):
    bpy.ops.wm.usd_export(filepath=output_path, selected_objects_only=True, export_materials=True, export_geometry=False)

# Function to create master USD file
def create_master_usd(output_directory, asset_name):
    # Same implementation as before

# Function to import USD file
def import_usd(filepath):
    bpy.ops.wm.usd_import(filepath=filepath)


class OBJECT_OT_usd_manager_panel(bpy.types.Panel):
    """Creates a panel for the USD Asset Manager"""
    bl_label = "USD Asset Manager"
    bl_idname = "USD_Manager"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category = 'scene'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.export_geometry_as_usd")

        row = layout.row()
        row.operator("object.export_materials_as_usd")

        row = layout.row()
        row.operator("object.import_usd_file")


# Define the custom operator classes
class OBJECT_OT_export_geometry_as_usd(bpy.types.Operator, ImportHelper):
    """Export Geometry as USD"""
    bl_idname = "object.export_geometry_as_usd"
    bl_label = "Export Geometry as USD"
    bl_description = "Export selected objects' geometry as a USD file"

    # Define the file path property
    filepath: bpy.props.StringProperty(
        name="Output Directory",
        description="Choose the directory to export USD assets",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    def execute(self, context):
        export_geometry(self.filepath)
        self.report({'INFO'}, "Geometry Exported Successfully")
        return {'FINISHED'}

class OBJECT_OT_export_materials_as_usd(bpy.types.Operator, ImportHelper):
    """Export Materials as USD"""
    bl_idname = "object.export_materials_as_usd"
    bl_label = "Export Materials as USD"
    bl_description = "Export selected objects' materials as a USD file"

    # Define the file path property
    filepath: bpy.props.StringProperty(
        name="Output Directory",
        description="Choose the directory to export USD assets",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    def execute(self, context):
        export_materials(self.filepath)
        self.report({'INFO'}, "Materials Exported Successfully")
        return {'FINISHED'}

class OBJECT_OT_import_usd_file(bpy.types.Operator, ImportHelper):
    """Import USD File"""
    bl_idname = "object.import_usd_file"
    bl_label = "Import USD File"
    bl_description = "Import a USD file into the scene"

    # Define the file path property
    filepath: bpy.props.StringProperty(
        name="USD File",
        description="Choose the USD file to import",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    def execute(self, context):
        import_usd(self.filepath)
        self.report({'INFO'}, "USD File Imported Successfully")
        return {'FINISHED'}

# Register the classes
def register():
    bpy.utils.register_class(OBJECT_OT_export_geometry_as_usd)
    bpy.utils.register_class(OBJECT_OT_export_materials_as_usd)
    bpy.utils.register_class(OBJECT_OT_import_usd_file)
    bpy.utils.register_class(OBJECT_OT_usd_manager_panel)

# Unregister the classes
def unregister():
    bpy.utils.unregister_class(OBJECT_OT_export_geometry_as_usd)
    bpy.utils.unregister_class(OBJECT_OT_export_materials_as_usd)
    bpy.utils.unregister_class(OBJECT_OT_import_usd_file)
    bpy.utils.unregister_class(OBJECT_OT_usd_manager_panel)

if __name__ == "__main__":
    register()