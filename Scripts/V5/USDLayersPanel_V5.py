bl_info = {
    "name": "USD Asset Manager",
    "author": "SMUELDigital",
    "version": (1, 1),
    "blender": (4, 2, 0),
    "location": "PROPERTIES",
    "description": "Create layers for all assets in a stage structure. This addon is located in the collection properties under exporters.",
    "warning": "This is an addon for a basic stage setup. You still need to do some manual work on the export side. In the best case you create an export preset under exporters for collections.",
    "doc_url": "https://github.com/SMUELDigital/Blender-USD-Manager-Addon",
    "category": "Object"
}


import bpy
import os

class USDPanel(bpy.types.Panel):
    bl_label = "USD Layers Panel"
    bl_idname = "USD_PANEL"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "collection"
    bl_category = "Exporters"

    def draw(self, context):
        layout = self.layout
        layout.label(text="USD Layers")

        # Create a button for importing a USD file
        layout.operator("wm.usd_import")

        # Create a button for exporting a USD file
        layout.operator("wm.usd_export")

        # Create a button for creating a new USD layer
        layout.operator("usd.create_layer")

        # Create a button for deleting the active USD layer
        layout.operator("usd.delete_layer")

class CreateUSDLayersOperator(bpy.types.Operator):
    bl_idname = "usd.create_layer"
    bl_label = "Create USD Layer"

    def execute(self, context):
        try:
            # Get the scene name
            scene_name = bpy.context.scene.name

            # Create a new empty/scope actor with the same name as the scene
            scope_actor = bpy.data.objects.new(scene_name, None)
            bpy.context.collection.objects.link(scope_actor)

            # Create sub-empties
            geo_empty = bpy.data.objects.new("/geo", None)
            material_empty = bpy.data.objects.new("/material", None)
            lights_empty = bpy.data.objects.new("/lights", None)
            extras_empty = bpy.data.objects.new("/extras", None)

            # Parent sub-empties to the scope actor
            geo_empty.parent = scope_actor
            material_empty.parent = scope_actor
            lights_empty.parent = scope_actor
            extras_empty.parent = scope_actor

            # Link sub-empties to the scene
            bpy.context.collection.objects.link(geo_empty)
            bpy.context.collection.objects.link(material_empty)
            bpy.context.collection.objects.link(lights_empty)
            bpy.context.collection.objects.link(extras_empty)

            # Get all objects in the scene
            objects = [obj for obj in bpy.context.scene.objects if obj.parent is None]

            # Parent objects to the corresponding sub-empty
            for obj in objects:
                if obj.type == 'MESH':
                    obj.parent = geo_empty
                elif obj.type == 'LIGHT':
                    obj.parent = lights_empty
                elif obj.type == 'CAMERA':
                    obj.parent = extras_empty
                elif obj.type == 'EMPTY' and obj.name.startswith("Material"):
                    obj.parent = material_empty
                else:
                    obj.parent = extras_empty


            # Add a USD exporter
            bpy.ops.collection.exporter_add('INVOKE_DEFAULT', name="IO_FH_usd")

            # Get the exporter
            exporter = bpy.context.scene.collection.exporters.get("IO_FH_usd")

            # Set the exporter properties
            if exporter:
                exporter.settings.selected_objects_only = False
                exporter.settings.visible_objects_only = True
                exporter.settings.export_animation = True

            # Set the file path
            op.filepath = os.path.splitext(bpy.data.filepath)[0] + ".usd"


            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

def auto_parent_handler(scene, depsgraph):
    # Get the scope actor
    scope_actor = bpy.context.view_layer.active_layer_collection.collection.objects.get(bpy.context.scene.name)

    # If the scope actor exists
    if scope_actor:
        # Get all sub-empties
        geo_empty = scope_actor.children.get("/geo")
        material_empty = scope_actor.children.get("/material")
        lights_empty = scope_actor.children.get("/lights")
        extras_empty = scope_actor.children.get("/extras")

        # Get all objects in the scene
        objects = [obj for obj in bpy.context.scene.objects if obj.parent is None]

        # Parent objects to the corresponding sub-empty
        for obj in objects:
            if obj.type == 'MESH':
                obj.parent = geo_empty
            elif obj.type == 'LIGHT':
                obj.parent = lights_empty
            elif obj.type == 'CAMERA':
                obj.parent = extras_empty
            elif obj.type == 'EMPTY' and obj.name.startswith("Material"):
                obj.parent = material_empty
            else:
                obj.parent = extras_empty

class DeleteUSDLayersOperator(bpy.types.Operator):
    bl_idname = "usd.delete_layer"
    bl_label = "Delete USD Layer"

    def execute(self, context):
        try:
            # Get the scope actor
            scope_actor = bpy.context.view_layer.active_layer_collection.collection.objects.get(bpy.context.scene.name)

            # If the scope actor exists, delete it
            if scope_actor:
                bpy.data.objects.remove(scope_actor)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "No scope actor to delete.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(USDPanel)
    bpy.utils.register_class(CreateUSDLayersOperator)
    bpy.utils.register_class(DeleteUSDLayersOperator)
    bpy.app.handlers.depsgraph_update_post.append(auto_parent_handler)

def unregister():
    bpy.utils.unregister_class(USDPanel)
    bpy.utils.unregister_class(CreateUSDLayersOperator)
    bpy.utils.unregister_class(DeleteUSDLayersOperator)
    bpy.app.handlers.depsgraph_update_post.remove(auto_parent_handler)

if __name__ == "__main__":
    register()
    
    