import bpy
from bpy.app.handlers import persistent
from .components_registry import get_components_registry
from .utils import redirect_c_stdout
from .utils import get_host_components
from .gizmos import update_gizmos
from ..utils import get_version
import io
import sys

previous_undo_steps_dump = ""
previous_undo_step_index = 0
file_loading = False


def migrate_components(migration_type):
    version = (0,0,0)
    global_version = get_version()
    migration_report = []
    if migration_type == 'GLOBAL':
        version = tuple(bpy.context.scene.HubsComponentsExtensionProperties.version)
        if version == global_version:
            return

    for scene in bpy.data.scenes:
        for component in get_host_components(scene):
            if migration_type == 'LOCAL':
                version = tuple(component.addon_version)
            try:
                component.migrate(migration_type, version, scene, migration_report)
                component.addon_version = global_version
            except:
                error = f"Error: Migration failed for component {component.get_display_name()} on scene \"{scene.name_full}\""
                migration_report.append(error)

    for ob in bpy.data.objects:
        for component in get_host_components(ob):
            if migration_type == 'LOCAL':
                version = tuple(component.addon_version)
            try:
                component.migrate(migration_type, version, ob, migration_report, ob=ob)
                component.addon_version = global_version
            except:
                error = f"Error: Migration failed for component {component.get_display_name()} on object \"{ob.name_full}\""
                migration_report.append(error)

        if ob.type == 'ARMATURE':
            for bone in ob.data.bones:
                for component in get_host_components(bone):
                    if migration_type == 'LOCAL':
                        version = tuple(component.addon_version)
                    try:
                        component.migrate(migration_type, version, bone, migration_report, ob=ob)
                        component.addon_version = global_version
                    except:
                        error = f"Error: Migration failed for component {component.get_display_name()} on bone \"{bone.name}\" in \"{ob.name_full}\""
                        migration_report.append(error)


    if migration_type == 'LOCAL':
        update_gizmos()

    if migration_report:
        def report_migration():
            bpy.ops.wm.hubs_report_viewer('INVOKE_DEFAULT', title="Component Migration Report", report_string='\n'.join(migration_report))
        bpy.app.timers.register(report_migration)


@persistent
def load_post(dummy):
    global previous_undo_steps_dump
    global previous_undo_step_index
    global file_loading
    previous_undo_steps_dump = ""
    previous_undo_step_index = 0
    file_loading = True
    migrate_components('GLOBAL')


@persistent
def version_update(dummy):
    from .. import (bl_info)
    bpy.context.scene.HubsComponentsExtensionProperties.version = bl_info['version'][0:3]


def find_active_undo_step_index(undo_steps):
    index = 0
    for step in undo_steps:
        if "[*" in step:
            return index

        index += 1

    return None


@persistent
def append_link_handler(dummy):
    global previous_undo_steps_dump
    global previous_undo_step_index
    global file_loading

    # Return if Blender isn't in a fully loaded state. (Prevents Blender crashing)
    if file_loading and not bpy.context.space_data:
        file_loading = False
        return

    file_loading = False

    # Get a representation of the undo stack.
    binary_stream = io.BytesIO()

    with redirect_c_stdout(binary_stream):
        bpy.context.window_manager.print_undo_steps()

    undo_steps_dump = binary_stream.getvalue().decode(sys.stdout.encoding)
    binary_stream.close()

    if undo_steps_dump == previous_undo_steps_dump:
        # The undo stack hasn't changed, so return early.  Note: this prevents modal operators (and anything else) from triggering things repeatedly when nothing has changed.
        return

    # Convert the undo stack representation into a list of undo steps (removing the unneeded header and footer in the process) and find the active undo step index.
    undo_steps = undo_steps_dump.split("\n")[1:-1]
    undo_step_index = find_active_undo_step_index(undo_steps)

    # Handle the current undo step.  This is needed for do, redo, and undo because the step holds the unmodified data, so the migration needs to be applied each time it becomes active.
    active_undo_step = undo_steps[undo_step_index]
    undo_name = active_undo_step.split("name=")[-1][1:-1]

    if undo_name in {'Append', 'Link'}:
        migrate_components('LOCAL')

    # Store things for comparison next time.
    previous_undo_steps_dump = undo_steps_dump
    previous_undo_step_index = undo_step_index


def register():
    if not load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post)

    if not version_update in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(version_update)

    if not append_link_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(append_link_handler)


def unregister():
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)

    if version_update in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(version_update)

    if append_link_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(append_link_handler)
