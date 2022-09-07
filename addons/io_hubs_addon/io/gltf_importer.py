import bpy
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
from io_scene_gltf2.blender.imp.gltf2_blender_node import BlenderNode
from io_scene_gltf2.blender.imp.gltf2_blender_material import BlenderMaterial
from io_scene_gltf2.blender.imp.gltf2_blender_scene import BlenderScene
from io_scene_gltf2.blender.imp.gltf2_blender_image import BlenderImage
from .utils import HUBS_CONFIG
from ..components.components_registry import get_component_by_name, get_components_registry
import traceback

EXTENSION_NAME = HUBS_CONFIG["gltfExtensionName"]

armatures = {}


def import_hubs_components(gltf_node, blender_object, import_settings):
    if gltf_node and gltf_node.extensions and EXTENSION_NAME in gltf_node.extensions:
        components_data = gltf_node.extensions[EXTENSION_NAME]
        for component_name in components_data.keys():
            component_class = get_component_by_name(component_name)
            if component_class:
                component_value = components_data[component_name]
                try:
                    component_class.gather_import(
                        import_settings, blender_object, component_name, component_value)
                except Exception:
                    traceback.print_exc()
            else:
                print('Could not import unsupported component "%s"' %
                      (component_name))


def add_lightmap(gltf_material, blender_mat, import_settings):
    if gltf_material and gltf_material.extensions and 'MOZ_lightmap' in gltf_material.extensions:
        extension = gltf_material.extensions['MOZ_lightmap']

        texture_index = extension['index']

        gltf_texture = import_settings.data.textures[texture_index]
        texture_extensions = gltf_texture.extensions
        if texture_extensions and texture_extensions.get('MOZ_texture_rgbe'):
            source = gltf_texture.extensions['MOZ_texture_rgbe']['source']
        else:
            source = gltf_texture.source

        BlenderImage.create(
            import_settings, source)
        pyimg = import_settings.data.images[source]
        blender_image_name = pyimg.blender_image_name
        blender_image = bpy.data.images[blender_image_name]
        if pyimg.mime_type == "image/vnd.radiance":
            blender_image.colorspace_settings.name = "Linear"

        blender_mat.use_nodes = True
        nodes = blender_mat.node_tree.nodes
        lightmap_node = nodes.new('moz_lightmap.node')
        lightmap_node.location = (-300, 0)
        lightmap_node.intensity = extension['intensity']
        node_tex = nodes.new('ShaderNodeTexImage')
        node_tex.image = blender_image
        node_tex.location = (-600, 0)
        blender_mat.node_tree.links.new(
            node_tex.outputs["Color"], lightmap_node.inputs["Lightmap"])
        node_uv = nodes.new('ShaderNodeUVMap')
        node_uv.uv_map = 'UVMap.%03d' % 1
        node_uv.location = (-900, 0)
        blender_mat.node_tree.links.new(
            node_uv.outputs["UV"], node_tex.inputs["Vector"])


def add_bones(import_settings):
    # Bones are created after the armatures so we need to wait until all nodes have been processed to be able to access the bones objects
    global armatures
    for armature in armatures.values():
        blender_object = armature['armature']
        for gltf_bone, bone in zip(armature['gltf_bones'], blender_object.data.bones):
            import_hubs_components(
                gltf_bone, bone, import_settings)


def glTF2_pre_import_callback(import_settings):
    for ob in bpy.context.view_layer.objects:
        component_list = ob.hubs_component_list

        registered_hubs_components = get_components_registry()

        if component_list.items:
            for component_item in component_list.items:
                component_name = component_item.name
                if component_name in registered_hubs_components:
                    component_class = registered_hubs_components[component_name]
                    component_class.pre_import(import_settings, ob)


def glTF2_post_import_callback(import_settings):
    for ob in bpy.context.view_layer.objects:
        component_list = ob.hubs_component_list

        registered_hubs_components = get_components_registry()

        if component_list.items:
            for component_item in component_list.items:
                component_name = component_item.name
                if component_name in registered_hubs_components:
                    component_class = registered_hubs_components[component_name]
                    component_class.post_import(import_settings, ob)


class glTF2ImportUserExtension:

    def __init__(self):
        self.extensions = [
            Extension(name=EXTENSION_NAME, extension={}, required=True)]
        self.properties = bpy.context.scene.hubs_import_properties

    def gather_import_scene_before_hook(self, gltf_scene, blender_scene, import_settings):
        if not self.properties.enabled:
            return

        global armatures
        armatures.clear()

        if import_settings.data.asset and import_settings.data.asset.extras:
            if 'gltf_yup' in import_settings.data.asset.extras:
                import_settings.import_settings['gltf_yup'] = import_settings.data.asset.extras[
                    'gltf_yup']

    def gather_import_scene_after_nodes_hook(self, gltf_scene, blender_scene, import_settings):
        if not self.properties.enabled:
            return

        import_hubs_components(gltf_scene, blender_scene, import_settings)

        add_bones(import_settings)
        armatures.clear()

    def gather_import_scene_before_hook(self, gltf_scene, blender_scene, import_settings):
        if not self.properties.enabled:
            return

        glTF2_pre_import_callback(import_settings)

    def gather_import_scene_after_animation_hook(self, gltf_scene, blender_scene, import_settings):
        if not self.properties.enabled:
            return

        glTF2_post_import_callback(import_settings)

    def gather_import_node_after_hook(self, vnode, gltf_node, blender_object, import_settings):
        if not self.properties.enabled:
            return

        import_hubs_components(
            gltf_node, blender_object, import_settings)

        # Node hooks are not called for bones. Bones are created together with their armature.
        # Unfortunately the bones are created after this hook is called so we need to wait until all nodes have been created.
        if vnode.is_arma:
            global armatures
            armatures[vnode.blender_object.name] = {'armature': vnode.blender_object, 'gltf_bones': [
                import_settings.data.nodes[child_index] for child_index in vnode.children if import_settings.vnodes[child_index].type == vnode.Bone]}

    def gather_import_image_after_hook(self, gltf_img, blender_image, import_settings):
        # As of Blender 3.2.0 the importer doesn't import images that are not referenced by a material socket.
        # We handle this case by case in each component's gather_import override.
        pass

    def gather_import_texture_after_hook(self, gltf_texture, node_tree, mh, tex_info, location, label, color_socket, alpha_socket, is_data, import_settings):
        # As of Blender 3.2.0 the importer doesn't import textures that are not referenced by a material socket image.
        # We handle this case by case in each component's gather_import override.
        pass

    def gather_import_material_after_hook(self, gltf_material, vertex_color, blender_mat, import_settings):
        if not self.properties.enabled:
            return

        import_hubs_components(
            gltf_material, blender_mat, import_settings)

        add_lightmap(gltf_material, blender_mat, import_settings)


# import hooks were only recently added to the glTF exporter, so make a custom hook for now
orig_BlenderNode_create_object = BlenderNode.create_object
orig_BlenderMaterial_create = BlenderMaterial.create
orig_BlenderScene_create = BlenderScene.create


@ staticmethod
def patched_BlenderNode_create_object(gltf, vnode_id):
    blender_object = orig_BlenderNode_create_object(gltf, vnode_id)

    vnode = gltf.vnodes[vnode_id]
    node = None

    if vnode.camera_node_idx is not None:
        parent_vnode = gltf.vnodes[vnode.parent]
        if parent_vnode.name:
            node = [n for n in gltf.data.nodes if n.name == parent_vnode.name][0]

    else:
        if vnode.name:
            node = [n for n in gltf.data.nodes if n.name == vnode.name][0]

    import_hubs_components(node, vnode.blender_object, gltf)

    # Node hooks are not called for bones. Bones are created together with their armature.
    # Unfortunately the bones are created after this hook is called so we need to wait until all nodes have been created.
    if vnode.is_arma:
        global armatures
        armatures[vnode.blender_object.name] = {'armature': vnode.blender_object, 'gltf_bones': [
            gltf.data.nodes[child_index] for child_index in vnode.children if gltf.vnodes[child_index].type == vnode.Bone]}

    return blender_object


@ staticmethod
def patched_BlenderMaterial_create(gltf, material_idx, vertex_color):
    orig_BlenderMaterial_create(
        gltf, material_idx, vertex_color)
    gltf_material = gltf.data.materials[material_idx]
    blender_mat_name = next(iter(gltf_material.blender_material.values()))
    blender_mat = bpy.data.materials[blender_mat_name]
    import_hubs_components(gltf_material, blender_mat, gltf)

    add_lightmap(gltf_material, blender_mat, gltf)


@ staticmethod
def patched_BlenderScene_create(gltf):
    global armatures
    armatures.clear()

    glTF2_pre_import_callback(gltf)

    orig_BlenderScene_create(gltf)
    gltf_scene = gltf.data.scenes[gltf.data.scene]
    blender_object = bpy.data.scenes[gltf.blender_scene]
    import_hubs_components(gltf_scene, blender_object, gltf)

    # Bones are created after the armatures so we need to wait until all nodes have been processed to be able to access the bones objects
    add_bones(gltf)
    armatures.clear()

    glTF2_post_import_callback(gltf)


def register():
    print("Register glTF Importer")
    if bpy.app.version < (3, 0, 0):
        BlenderNode.create_object = patched_BlenderNode_create_object
        BlenderMaterial.create = patched_BlenderMaterial_create
        BlenderScene.create = patched_BlenderScene_create


def unregister():
    print("Unregister glTF Importer")
    if bpy.app.version < (3, 0, 0):
        BlenderNode.create_object = orig_BlenderNode_create_object
        BlenderMaterial.create = orig_BlenderMaterial_create
        BlenderScene.create = orig_BlenderScene_create
