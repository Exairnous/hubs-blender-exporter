import bpy


def load_gizmo_model(id, path):
    assert id != None, "No Gizmo id provided"
    assert path != None, "No Gizmo path provided"

    custom_shape_verts = []
    print("Gizmo model " + id + " load start: " + path)
    bpy.ops.import_scene.gltf(filepath=path)
    obj = bpy.data.objects[id]

    obj.data.calc_loop_triangles()
    for tri in obj.data.loop_triangles:
        for index in range(0, len(tri.vertices)):
            v = obj.data.vertices[tri.vertices[index]]
            co_final = obj.matrix_world @ v.co
            custom_shape_verts.append([co_final[0], co_final[1], co_final[2]])

    print(str(custom_shape_verts))
    bpy.data.objects.remove(obj, do_unlink=True)
    print("Gizmo model load end")

    return custom_shape_verts
