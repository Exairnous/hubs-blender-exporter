import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, CollectionProperty, PointerProperty
from bpy.types import Operator
from . import components
from functools import reduce

class AddHubsComponent(Operator):
    bl_idname = "wm.add_hubs_component"
    bl_label = "Add Hubs Component"
    bl_property = "component_name"

    object_source: StringProperty(name="object_source")
    component_name: StringProperty(name="component_name")

    def execute(self, context):
        if self.component_name == '':
            return

        obj = components.get_object_source(context, self.object_source)

        components.add_component(
            obj,
            self.component_name,
            context.scene.hubs_settings.hubs_config,
            context.scene.hubs_settings.registered_hubs_components
        )

        context.area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        object_source = self.object_source
        hubs_components = bpy.context.scene.hubs_settings.registered_hubs_components

        def sort_by_category(acc, v):
            (component_name, component_class) = v
            category = component_class.definition.get("category", "Misc")
            acc[category] = acc.get(category, [])
            acc[category].append(v)
            return acc

        components_by_category = reduce(sort_by_category, hubs_components.items(), {})
        obj = components.get_object_source(context, object_source)

        def draw(self, context):
            row = self.layout.row()
            for category, cmps in components_by_category.items():
                column = row.column()
                column.label(text=category)
                for (component_name, component_class) in cmps:
                    component_display_name = components.dash_to_title(component_name)
                    if not components.is_object_source_component(object_source, component_class.definition): continue

                    if components.has_component(obj, component_name):
                        column.label(text=component_display_name)
                    else:
                        op = column.operator(AddHubsComponent.bl_idname, text = component_display_name, icon='ADD')
                        op.component_name = component_name
                        op.object_source = object_source

        bpy.context.window_manager.popup_menu(draw)

        return {'RUNNING_MODAL'}

class RemoveHubsComponent(Operator):
    bl_idname = "wm.remove_hubs_component"
    bl_label = "Remove Hubs Component"

    object_source: StringProperty(name="object_source")
    component_name: StringProperty(name="component_name")

    def execute(self, context):
        if self.component_name == '':
            return
        obj = components.get_object_source(context, self.object_source)
        components.remove_component(obj, self.component_name)
        context.area.tag_redraw()
        return {'FINISHED'}

class AddHubsComponentItem(Operator):
    bl_idname = "wm.add_hubs_component_item"
    bl_label = "Add a new item"

    path: StringProperty(name="path")

    def execute(self, context):
        parts = self.path.split(".")

        cur_obj = context

        for part in parts:
            try:
                index = int(part)
                cur_obj = cur_obj[index]
            except:
                cur_obj = getattr(cur_obj, part)

        cur_obj.add()

        context.area.tag_redraw()

        return{'FINISHED'}

class CopyHubsComponent(Operator):
    bl_idname = "wm.copy_hubs_component"
    bl_label = "Copy component from active object"

    component_name: StringProperty(name="component_name")

    def execute(self, context):
        src_obj = context.active_object
        dest_objs = filter(lambda item: src_obj != item, context.selected_objects)

        hubs_settings = context.scene.hubs_settings
        component_class = hubs_settings.registered_hubs_components[self.component_name]
        component_class_name = component_class.__name__
        component_definition = hubs_settings.hubs_config['components'][self.component_name]

        if components.has_component(src_obj, self.component_name):
            for dest_obj in dest_objs:
                if components.has_component(dest_obj, self.component_name):
                    components.remove_component(dest_obj, self.component_name)

                components.add_component(
                    dest_obj,
                    self.component_name,
                    hubs_settings.hubs_config,
                    hubs_settings.registered_hubs_components
                )

                src_component = getattr(src_obj, component_class_name)
                dest_component = getattr(dest_obj, component_class_name)

                self.copy_type(hubs_settings, src_component, dest_component, component_definition)

        return{'FINISHED'}


    def copy_type(self, hubs_settings, src_obj, dest_obj, type_definition):
        for property_name, property_definition in type_definition['properties'].items():
            self.copy_property(hubs_settings, src_obj, dest_obj, property_name, property_definition)

    def copy_property(self, hubs_settings, src_obj, dest_obj, property_name, property_definition):
        property_type = property_definition['type']

        if property_type == 'collections':
            return

        registered_types = hubs_settings.hubs_config['types']
        is_custom_type = property_type in registered_types

        src_property = getattr(src_obj, property_name)
        dest_property = getattr(dest_obj, property_name)

        if is_custom_type:
            dest_obj[property_name] = self.copy_type(hubs_settings, src_property, dest_property, registered_types[property_type])
        elif property_type == 'array':
            self.copy_array_property(hubs_settings, src_property, dest_property, property_definition)
        else:
            setattr(dest_obj, property_name, src_property)

    def copy_array_property(self, hubs_settings, src_arr, dest_arr, property_definition):
        array_type = property_definition['arrayType']
        registered_types = hubs_settings.hubs_config['types']
        type_definition = registered_types[array_type]

        dest_arr.clear()

        for src_item in src_arr:
            dest_item = dest_arr.add()
            self.copy_type(hubs_settings, src_item, dest_item, type_definition)


class RemoveHubsComponentItem(Operator):
    bl_idname = "wm.remove_hubs_component_item"
    bl_label = "Remove an item"

    path: StringProperty(name="path")

    def execute(self, context):
        parts = self.path.split(".")

        index = int(parts.pop())

        cur_obj = context

        for part in parts:
            try:
                cur_index = int(part)
                cur_obj = cur_obj[cur_index]
            except:
                cur_obj = getattr(cur_obj, part)

        cur_obj.remove(index)

        context.area.tag_redraw()

        return{'FINISHED'}

class ReloadHubsConfig(Operator):
    bl_idname = "wm.reload_hubs_config"
    bl_label = "Reload Hubs Config"

    def execute(self, context):
        context.scene.hubs_settings.reload_config()
        context.area.tag_redraw()
        return {'FINISHED'}

class ResetHubsComponentNames(Operator):
    bl_idname = "wm.reset_hubs_component_names"
    bl_label = "Reset Selected Hubs Component Names and Ids"

    def execute(self, context):
        for obj in context.selected_objects:
            if components.has_component(obj, "kit-piece"):
                kit_piece = obj.hubs_component_kit_piece
                kit_piece.name = obj.name
                kit_piece.id = obj.name

            if components.has_component(obj, "kit-alt-materials"):
                alt_materials = obj.hubs_component_kit_alt_materials
                alt_materials.name = obj.name
                alt_materials.id = obj.name

        return {'FINISHED'}

class UVScrollPreviewOperator(Operator):
    """Preview UV Scrolling"""
    bl_idname = "object.preview_uv_scroll"
    bl_label = "Preview UV Scroll"

    _timer = None
    reset = False
    finished = False
    orig_mode = None
    speed_unit = 0.01277
    step_x = 0
    step_y = 0
    reset_step_x = False
    reset_step_y = False

    def modal(self, context, event):
        obj = context.active_object

        if obj.mode != 'OBJECT':
            self.orig_mode = obj.mode
            obj.hubs_component_uv_scroll.preview = False
            self.finished = True
            bpy.ops.object.mode_set(mode='OBJECT')

        if event.type == 'ESC' or not obj.hubs_component_uv_scroll.preview:
            obj.hubs_component_uv_scroll.preview = False
            self.finished = True

        if event.type == 'TIMER':
            idx = 0
            resetting = False
            new_uv_positions = []

            speed_x = obj.hubs_component_uv_scroll.speed[0]
            speed_y = obj.hubs_component_uv_scroll.speed[1] * -1
            increment_x = abs(obj.hubs_component_uv_scroll.increment[0])
            increment_y = abs(obj.hubs_component_uv_scroll.increment[1])
            move_x = self.speed_unit * speed_x
            move_y = self.speed_unit * speed_y

            self.step_x += move_x
            self.step_y += move_y

            for polygon in obj.data.polygons:
                for vert, loop_idx in zip(polygon.vertices, polygon.loop_indices):
                    uv_coords = obj.data.uv_layers.active.data[loop_idx].uv

                    if self.reset:
                        resetting = True
                        uv_coords.x = self.orig_uv_position[idx][0]
                        uv_coords.y = self.orig_uv_position[idx][1]

                    else:
                        if not increment_x:
                            uv_coords.x += move_x
                        else:
                            if abs(self.step_x) >= increment_x:
                                uv_coords.x += increment_x if speed_x > 0 else -increment_x
                                self.reset_step_x = True

                        if not increment_y:
                            uv_coords.y += move_y
                        else:
                            if abs(self.step_y) >= increment_y:
                                uv_coords.y += increment_y if speed_y > 0 else -increment_y
                                self.reset_step_y = True

                        new_uv_positions.append((uv_coords.x, uv_coords.y))

                    idx += 1

            if self.reset_step_x:
                self.step_x = 0
                self.reset_step_x = False

            if self.reset_step_y:
                self.step_y = 0
                self.reset_step_y = False

            if resetting:
                self.reset = False

            else:
                if (abs(new_uv_positions[0][0]) >= abs(self.orig_uv_position[0][0]) + 1
                or  abs(new_uv_positions[0][1]) >= abs(self.orig_uv_position[0][1]) + 1):
                    self.reset = True

            if self.finished:
                idx = 0
                for polygon in obj.data.polygons:
                    for vert, loop_idx in zip(polygon.vertices, polygon.loop_indices):
                        uv_coords = obj.data.uv_layers.active.data[loop_idx].uv
                        uv_coords.x = self.orig_uv_position[idx][0]
                        uv_coords.y = self.orig_uv_position[idx][1]
                        idx += 1

                context.window_manager.event_timer_remove(self._timer)
                bpy.ops.object.mode_set(mode=self.orig_mode)
                return {'FINISHED'}



        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        obj = context.active_object
        self.orig_mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        self.orig_uv_position = []

        for polygon in obj.data.polygons:
            for vert, loop_idx in zip(polygon.vertices, polygon.loop_indices):
                uv_coords = obj.data.uv_layers.active.data[loop_idx].uv
                self.orig_uv_position.append((uv_coords.x, uv_coords.y))

        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class UVScrollPreviewExecOperator(Operator):
    """Preview UV Scrolling"""
    bl_idname = "object.preview_uv_scroll_exec"
    bl_label = "Preview UV Scroll Exec"

    def execute(self, context):
        obj = context.active_object

        if not obj.hubs_component_uv_scroll.preview:
            obj.hubs_component_uv_scroll.preview = True
            bpy.ops.object.preview_uv_scroll('INVOKE_DEFAULT')

        else:
            obj.hubs_component_uv_scroll.preview = False

        return {'FINISHED'}

def register():
    bpy.utils.register_class(AddHubsComponent)
    bpy.utils.register_class(RemoveHubsComponent)
    bpy.utils.register_class(CopyHubsComponent)
    bpy.utils.register_class(AddHubsComponentItem)
    bpy.utils.register_class(RemoveHubsComponentItem)
    bpy.utils.register_class(ReloadHubsConfig)
    bpy.utils.register_class(ResetHubsComponentNames)
    bpy.utils.register_class(UVScrollPreviewOperator)
    bpy.utils.register_class(UVScrollPreviewExecOperator)

def unregister():
    bpy.utils.unregister_class(AddHubsComponent)
    bpy.utils.unregister_class(RemoveHubsComponent)
    bpy.utils.unregister_class(CopyHubsComponent)
    bpy.utils.unregister_class(AddHubsComponentItem)
    bpy.utils.unregister_class(RemoveHubsComponentItem)
    bpy.utils.unregister_class(ReloadHubsConfig)
    bpy.utils.unregister_class(ResetHubsComponentNames)
    bpy.utils.unregister_class(UVScrollPreviewOperator)
    bpy.utils.unregister_class(UVScrollPreviewExecOperator)
