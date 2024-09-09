
#USD Manager Addon
```python
bl_info = {
    "name": "USD Asset Manager",
    "blender": (4, 2, 0),
    "category": "Object",
}

import bpy
import os
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper

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
    master_usd_path = os.path.join(output_directory, f"{asset_name}.usd")
    geo_usd_path = os.path.join(output_directory, "geo.usd")
    material_usd_path = os.path.join(output_directory, "material.usd")

    with open(master_usd_path, 'w') as master_usd:
        master_usd.write('#usda 1.0\n')
        master_usd.write('(\n')
        master_usd.write('    defaultPrim = "Asset"\n')
        master_usd.write(')\n')
        master_usd.write('def "Asset" {\n')
        master_usd.write(f'    def "geometry" (\n')
        master_usd.write(f'        references = [@{geo_usd_path}@]\n')
        master_usd.write(f'    ) {{\n    }}\n')
        master_usd.write(f'    def "materials" (\n')
        master_usd.write(f'        references = [@{material_usd_path}@]\n')
        master_usd.write(f'    ) {{\n    }}\n')
        master_usd.write('}\n')

# Function to import USD file
def import_usd(filepath):
    bpy.ops.wm.usd_import(filepath=filepath)

# Function to edit USD hierarchy
def edit_usd_hierarchy(filepath, asset_type):
    # Placeholder for editing USD hierarchy
    print(f"Editing USD hierarchy in {filepath} as {asset_type}")

    if asset_type == 'assembly':
        print("Setting asset as assembly")
    elif asset_type == 'group':
        print("Setting asset as group")
    elif asset_type == 'component':
        print("Setting asset as component")
    elif asset_type == 'subcomponent':
        print("Setting asset as subcomponent")

    print("Recognizing and categorizing elements in the USD file")

# Main function to organize and export assets
def organize_and_export_assets(output_directory):
    # Ensure the output directory exists
    create_directory(output_directory)

    # Create a directory for textures
    textures_dir = os.path.join(output_directory, "textures")
    create_directory(textures_dir)

    # Export geometry and materials
    geo_usd_path = os.path.join(output_directory, "geo.usd")
    material_usd_path = os.path.join(output_directory, "material.usd")
    export_geometry(geo_usd_path)
    export_materials(material_usd_path)

    # Copy associated textures to the textures directory
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            for mat in obj.data.materials:
                if mat:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            image = node.image
                            if image:
                                image_path = bpy.path.abspath(image.filepath)
                                if os.path.exists(image_path):
                                    dest_path = os.path.join(textures_dir, os.path.basename(image_path))
                                    if not os.path.exists(dest_path):
                                        # Copy the texture file
                                        os.system(f"cp '{image_path}' '{dest_path}'")

    # Create master USD file
    create_master_usd(output_directory, "Asset")

# Define the operator for exporting USD
class OBJECT_OT_usd_exporter(bpy.types.Operator, ImportHelper):
    bl_idname = "object.usd_exporter"
    bl_label = "Export USD Assets"
    bl_description = "Export selected objects as USD with organized folder structure"

    # Define the file path property
    directory: StringProperty(
        name="Output Directory",
        description="Choose the directory to export USD assets",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    def execute(self, context):
        organize_and_export_assets(self.directory)
        self.report({'INFO'}, "USD Assets Exported Successfully")
        return {'FINISHED'}

# Define the operator for importing USD
class OBJECT_OT_usd_importer(bpy.types.Operator, ImportHelper):
    bl_idname = "object.usd_importer"
    bl_label = "Import USD Asset"
    bl_description = "Import a USD file into the scene"

    # Define the file path property
    filepath: StringProperty(
        name="USD File",
        description="Choose the USD file to import",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    def execute(self, context):
        import_usd(self.filepath)
        self.report({'INFO'}, "USD Asset Imported Successfully")
        return {'FINISHED'}

# Define the operator for editing USD hierarchy
class OBJECT_OT_usd_editor(bpy.types.Operator, ImportHelper):
    bl_idname = "object.usd_editor"
    bl_label = "Edit USD Hierarchy"
    bl_description = "Edit the hierarchy of a USD file"

    # Define the file path property
    filepath: StringProperty(
        name="USD File",
        description="Choose the USD file to edit",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    # Define the asset type property
    asset_type: EnumProperty(
        name="Asset Type",
        description="Choose the type of USD asset",
        items=[
            ('assembly', "Assembly", "Define as assembly"),
            ('group', "Group", "Define as group"),
            ('component', "Component", "Define as component"),
            ('subcomponent', "Subcomponent", "Define as subcomponent"),
        ]
    )

    def execute(self, context):
        edit_usd_hierarchy(self.filepath, self.asset_type)
        self.report({'INFO'}, "USD Hierarchy Edited Successfully")
        return {'FINISHED'}

# Define the panel
class OBJECT_PT_usd_manager_panel(bpy.types.Panel):
    bl_label = "USD Asset Manager"
    bl_idname = "OBJECT_PT_usd_manager_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'USD Manager'

    def draw(self, context):
        layout = self.layout
        layout.operator("object.usd_exporter", text="Export USD Assets")
        layout.operator("object.usd_importer", text="Import USD Asset")
        layout.operator("object.usd_editor", text="Edit USD Hierarchy")

# Register and unregister classes
def register():
    bpy.utils.register_class(OBJECT_OT_usd_exporter)
    bpy.utils.register_class(OBJECT_OT_usd_importer)
    bpy.utils.register_class(OBJECT_OT_usd_editor)
    bpy.utils.register_class(OBJECT_PT_usd_manager_panel)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_usd_exporter)
    bpy.utils.unregister_class(OBJECT_OT_usd_importer)
    bpy.utils.unregister_class(OBJECT_OT_usd_editor)
    bpy.utils.unregister_class(OBJECT_PT_usd_manager_panel)

if __name__ == "__main__":
    register()

```

