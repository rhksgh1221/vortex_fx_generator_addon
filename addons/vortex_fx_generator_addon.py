bl_info = {
    "name": "Vortex FX Generator",
    "author": "ChatGPT",
    "version": (1, 0, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > VFX > Vortex FX",
    "description": "Generate stylized abyss, nebula, crystal, electric and petal vortex VFX meshes.",
    "category": "Add Mesh",
}

import bpy
import math
import random
from mathutils import Vector, Euler
from bpy.props import EnumProperty, IntProperty, FloatProperty, BoolProperty, FloatVectorProperty, PointerProperty

TAU = math.tau
COLLECTION_NAME = "VFX_Vortex_Generated"

STYLE_TABLE = {
    "ABYSS_ROSE": dict(name="Abyss Rose", turn=1.35, width=1.15, noise=.75, height=.45, jag=.25, arcs=10, sparks=1.0),
    "NEBULA_RIFT": dict(name="Nebula Rift", turn=1.10, width=1.65, noise=1.35, height=.75, jag=.45, arcs=7, sparks=1.4),
    "CRYSTAL_SWIRL": dict(name="Crystal Swirl", turn=.95, width=.80, noise=.55, height=.32, jag=.90, arcs=14, sparks=1.8),
    "ELECTRIC_SPIRAL": dict(name="Electric Spiral", turn=1.55, width=.45, noise=1.85, height=.52, jag=1.20, arcs=22, sparks=2.4),
    "PETAL_VORTEX": dict(name="Petal Vortex", turn=1.0, width=1.25, noise=.35, height=.25, jag=.10, arcs=5, sparks=.6),
}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def make_collection(context, clear=False):
    col = bpy.data.collections.get(COLLECTION_NAME)
    if col and clear:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
        col = None
    if col is None:
        col = bpy.data.collections.new(COLLECTION_NAME)
        context.scene.collection.children.link(col)
    return col


def make_mat(name, color, strength=1.0, alpha=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    mat.show_transparent_back = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new(type="ShaderNodeOutputMaterial")
    em = nodes.new(type="ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = strength
    if alpha is None:
        links.new(em.outputs["Emission"], out.inputs["Surface"])
    else:
        tr = nodes.new(type="ShaderNodeBsdfTransparent")
        mix = nodes.new(type="ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = 1.0 - alpha
        links.new(tr.outputs["BSDF"], mix.inputs[1])
        links.new(em.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def style_from_settings(s, rng):
    effect = s.effect_type
    if effect == "RANDOM":
        effect = rng.choice(list(STYLE_TABLE.keys()))
    return effect, STYLE_TABLE[effect]


def spiral_center(s, style, rng, arm_i, ring_i, p, phase, direction):
    base_radius = lerp(s.inner_radius, s.radius, p ** .82)
    angle = phase + direction * TAU * (s.turns * style['turn'] + ring_i * .08) * p
    angle += s.swirl * (p ** 1.45) * direction
    petal = math.sin((s.arms + ring_i + 1) * angle + ring_i * .63)
    n1 = math.sin((p * 9.0 + arm_i * 1.7 + ring_i * .9) * TAU)
    n2 = math.sin((p * 3.3 + arm_i * .31 + ring_i * .45) * TAU)
    noise = s.noise * style['noise'] * .06 * (n1 * .65 + n2 * .35)
    jag = style['jag'] * s.jaggedness * .055 * math.sin((p * 18.0 + arm_i * .37) * TAU)
    radius = base_radius * (1 + s.petal_amount * .11 * petal * math.sin(math.pi * p) + noise + jag)
    return Vector((math.cos(angle) * radius, math.sin(angle) * radius, s.height * style['height'] * math.sin(TAU * (p * 1.2 + arm_i * .13 + ring_i * .22)) * math.sin(math.pi * p)))


def build_ribbon(s, style, rng, arm_i, ring_i, mat, col, parent):
    direction = -1 if s.reverse else 1
    if s.alternate_direction and (arm_i + ring_i) % 2:
        direction *= -1
    segs = max(8, s.segments)
    phase = TAU * arm_i / max(1, s.arms) + ring_i * .27
    centers = [spiral_center(s, style, rng, arm_i, ring_i, i / (segs - 1), phase, direction) for i in range(segs)]
    verts, faces = [], []
    for i, c in enumerate(centers):
        p = i / (segs - 1)
        t = centers[min(i + 1, segs - 1)] - centers[max(i - 1, 0)]
        if t.length < 1e-6:
            t = Vector((1, 0, 0))
        t.normalize()
        n = Vector((-t.y, t.x, 0))
        if n.length < 1e-6:
            n = Vector((1, 0, 0))
        n.normalize()
        taper = math.sin(math.pi * p) ** max(.18, s.taper)
        pulse = 1 + .18 * math.sin(TAU * (p * 2 + arm_i * .17 + ring_i * .31))
        width = s.thickness * style['width'] * (1 - ring_i * .12) * (.18 + .82 * taper) * (1 - .22 * p) * pulse
        sharp = clamp(s.sharpness, 0, 1)
        verts.extend([c - n * width * (.5 + .3 * sharp), c + n * width * (.5 - .1 * sharp)])
    for i in range(segs - 1):
        faces.append((i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2))
    mesh = bpy.data.meshes.new(f"{style['name']}_Ribbon_{arm_i:02d}_{ring_i:02d}")
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    obj.data.materials.append(mat)
    obj.parent = parent
    col.objects.link(obj)
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            uv.data[li].uv = (vi // 2 / (segs - 1), float(vi % 2))
    return obj


def build_arc(s, style, rng, arc_i, mat, col, parent):
    curve = bpy.data.curves.new(f"{style['name']}_Arc_{arc_i:02d}", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 2
    curve.bevel_depth = s.arc_thickness * rng.uniform(.55, 1.45)
    curve.bevel_resolution = 1
    pts = max(8, int(s.segments * rng.uniform(.30, .55)))
    spl = curve.splines.new('POLY')
    spl.points.add(pts - 1)
    phase = rng.random() * TAU
    direction = -1 if (s.reverse ^ (rng.random() < .5)) else 1
    start_p, end_p = rng.uniform(.08, .34), rng.uniform(.62, 1.0)
    for i, point in enumerate(spl.points):
        p = lerp(start_p, end_p, i / (pts - 1))
        angle = phase + direction * TAU * (s.turns * style['turn'] * p + rng.uniform(-.035, .035))
        radius = lerp(s.inner_radius, s.radius * rng.uniform(.75, 1.05), p)
        jitter = s.noise * style['noise'] * rng.uniform(-.08, .08) * s.radius
        co = Vector((math.cos(angle) * (radius + jitter), math.sin(angle) * (radius + jitter), rng.uniform(-s.height, s.height) * .25))
        point.co = (co.x, co.y, co.z, 1)
    obj = bpy.data.objects.new(curve.name, curve)
    obj.data.materials.append(mat)
    obj.parent = parent
    col.objects.link(obj)
    return obj


def build_core_and_sparks(s, style, rng, mats, col, parent):
    if s.add_core:
        for r, mat in [(s.inner_radius * 1.4, mats['dark']), (s.inner_radius * 1.95, mats['accent'])]:
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=max(.006, s.arc_thickness), major_segments=96, minor_segments=6, location=(0, 0, 0))
            obj = bpy.context.object
            obj.name = f"{style['name']}_Core_Ring"
            obj.data.materials.append(mat)
            obj.parent = parent
            col.objects.link(obj)
            for c in list(obj.users_collection):
                if c != col:
                    c.objects.unlink(obj)
    if s.add_sparks:
        for i in range(int(s.spark_count * style['sparks'])):
            angle = rng.random() * TAU
            radius = rng.uniform(s.inner_radius, s.radius * 1.08)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=s.spark_size * rng.uniform(.45, 1.65), location=(math.cos(angle) * radius, math.sin(angle) * radius, rng.uniform(-s.height, s.height) * .35))
            obj = bpy.context.object
            obj.name = f"{style['name']}_Spark_{i:02d}"
            obj.data.materials.append(mats['highlight'] if rng.random() < .35 else mats['accent'])
            obj.parent = parent
            col.objects.link(obj)
            for c in list(obj.users_collection):
                if c != col:
                    c.objects.unlink(obj)


def linear_keys(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


class VortexFXSettings(bpy.types.PropertyGroup):
    effect_type: EnumProperty(name="Type", items=[("ABYSS_ROSE", "Abyss Rose", "Dark flower-like vortex"), ("NEBULA_RIFT", "Nebula Rift", "Wide smoky nebula vortex"), ("CRYSTAL_SWIRL", "Crystal Swirl", "Sharp glass-like swirl"), ("ELECTRIC_SPIRAL", "Electric Spiral", "Thin noisy lightning spiral"), ("PETAL_VORTEX", "Petal Vortex", "Clean blade/petal vortex"), ("RANDOM", "Random Mix", "Random style")], default="ABYSS_ROSE")
    seed: IntProperty(name="Seed", default=9147, min=0, max=999999)
    arms: IntProperty(name="Arms", default=14, min=1, max=64)
    rings: IntProperty(name="Layers", default=3, min=1, max=8)
    segments: IntProperty(name="Segments", default=128, min=8, max=512)
    radius: FloatProperty(name="Radius", default=3.45, min=.05, max=50)
    inner_radius: FloatProperty(name="Inner Radius", default=.28, min=0, max=10)
    thickness: FloatProperty(name="Ribbon Width", default=.20, min=.001, max=5)
    arc_thickness: FloatProperty(name="Arc Width", default=.015, min=.001, max=1)
    height: FloatProperty(name="Height", default=.55, min=0, max=20)
    turns: FloatProperty(name="Turns", default=1.45, min=.05, max=8)
    swirl: FloatProperty(name="Swirl", default=1.3, min=-8, max=8)
    petal_amount: FloatProperty(name="Petal Shape", default=.95, min=0, max=3)
    noise: FloatProperty(name="Noise", default=.78, min=0, max=5)
    jaggedness: FloatProperty(name="Jagged", default=.38, min=0, max=5)
    sharpness: FloatProperty(name="Sharp", default=.52, min=0, max=1)
    taper: FloatProperty(name="Taper", default=.75, min=.05, max=3)
    add_core: BoolProperty(name="Core Rings", default=True)
    add_arcs: BoolProperty(name="Electric Arcs", default=True)
    add_sparks: BoolProperty(name="Sparks", default=True)
    spark_count: IntProperty(name="Spark Count", default=58, min=0, max=1000)
    spark_size: FloatProperty(name="Spark Size", default=.035, min=.001, max=1)
    reverse: BoolProperty(name="Reverse", default=False)
    alternate_direction: BoolProperty(name="Alternate Direction", default=False)
    auto_clear: BoolProperty(name="Clear Before Generate", default=True)
    glow_power: FloatProperty(name="Glow Power", default=3.5, min=.01, max=30)
    primary_color: FloatVectorProperty(name="Primary", subtype='COLOR', size=4, default=(.08, .07, .10, .56), min=0, max=1)
    accent_color: FloatVectorProperty(name="Accent", subtype='COLOR', size=4, default=(.47, .03, .92, .78), min=0, max=1)
    highlight_color: FloatVectorProperty(name="Highlight", subtype='COLOR', size=4, default=(.92, .97, 1.0, 1.0), min=0, max=1)
    tilt_x: FloatProperty(name="Tilt X", default=0, min=-180, max=180)
    tilt_y: FloatProperty(name="Tilt Y", default=0, min=-180, max=180)
    roll_z: FloatProperty(name="Roll Z", default=0, min=-360, max=360)
    animate: BoolProperty(name="Animate Spin", default=True)
    frame_start: IntProperty(name="Start", default=1, min=1)
    frame_end: IntProperty(name="End", default=96, min=2)


class VORTEXFX_OT_generate(bpy.types.Operator):
    bl_idname = "vortexfx.generate"
    bl_label = "Generate Vortex FX"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        s = context.scene.vortex_fx_settings
        rng = random.Random(s.seed)
        _, style = style_from_settings(s, rng)
        col = make_collection(context, clear=s.auto_clear)
        parent = bpy.data.objects.new(f"VFX_Vortex_Controller_{style['name'].replace(' ', '_')}", None)
        parent.empty_display_type = 'PLAIN_AXES'
        parent.empty_display_size = max(.5, s.radius * .25)
        col.objects.link(parent)
        mats = dict(primary=make_mat(f"VFX_{style['name']}_Ribbon", tuple(s.primary_color), s.glow_power * .55, s.primary_color[3]), accent=make_mat(f"VFX_{style['name']}_Accent", tuple(s.accent_color), s.glow_power), highlight=make_mat(f"VFX_{style['name']}_Highlight", tuple(s.highlight_color), s.glow_power * 1.35), dark=make_mat(f"VFX_{style['name']}_DarkCore", (.005, .004, .008, .82), .08, .82))
        for ring_i in range(s.rings):
            for arm_i in range(s.arms):
                build_ribbon(s, style, rng, arm_i, ring_i, mats['primary'] if (arm_i + ring_i) % 3 else mats['accent'], col, parent)
        if s.add_arcs:
            for arc_i in range(int(style['arcs'] + s.arms * .25 + s.rings)):
                build_arc(s, style, rng, arc_i, mats['highlight'] if arc_i % 4 == 0 else mats['accent'], col, parent)
        build_core_and_sparks(s, style, rng, mats, col, parent)
        parent.rotation_euler = Euler((math.radians(s.tilt_x), math.radians(s.tilt_y), math.radians(s.roll_z)), 'XYZ')
        if s.animate:
            context.scene.frame_start = min(context.scene.frame_start, s.frame_start)
            context.scene.frame_end = max(context.scene.frame_end, s.frame_end)
            parent.keyframe_insert(data_path="rotation_euler", frame=s.frame_start)
            parent.rotation_euler.z += -TAU if s.reverse else TAU
            parent.keyframe_insert(data_path="rotation_euler", frame=s.frame_end)
            linear_keys(parent)
        context.view_layer.objects.active = parent
        parent.select_set(True)
        self.report({'INFO'}, f"Generated {style['name']} vortex FX")
        return {'FINISHED'}


class VORTEXFX_OT_randomize(bpy.types.Operator):
    bl_idname = "vortexfx.randomize"
    bl_label = "Randomize Vortex Settings"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        s = context.scene.vortex_fx_settings
        rng = random.Random()
        s.seed = rng.randint(1, 999999)
        s.effect_type = rng.choice(list(STYLE_TABLE.keys()))
        s.arms = rng.randint(6, 18); s.rings = rng.randint(1, 4); s.segments = rng.choice([64, 80, 96, 128])
        s.radius = rng.uniform(2, 5); s.inner_radius = rng.uniform(.15, .65); s.thickness = rng.uniform(.08, .36); s.arc_thickness = rng.uniform(.008, .035)
        s.height = rng.uniform(.1, 1.1); s.turns = rng.uniform(.75, 2.2); s.swirl = rng.uniform(.2, 2.6) * (-1 if rng.random() < .25 else 1)
        s.petal_amount = rng.uniform(0, 1.4); s.noise = rng.uniform(.15, 1.35); s.jaggedness = rng.uniform(0, 1.15); s.sharpness = rng.uniform(0, .85)
        s.taper = rng.uniform(.45, 1.15); s.spark_count = rng.randint(18, 90); s.spark_size = rng.uniform(.015, .065)
        s.reverse = rng.random() < .5; s.alternate_direction = rng.random() < .3
        return {'FINISHED'}


class VORTEXFX_OT_clear(bpy.types.Operator):
    bl_idname = "vortexfx.clear"
    bl_label = "Clear Vortex FX"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        make_collection(context, clear=True)
        return {'FINISHED'}


class VORTEXFX_OT_preset_image_like(bpy.types.Operator):
    bl_idname = "vortexfx.preset_image_like"
    bl_label = "Preset: Dark Spiral Like Reference"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        s = context.scene.vortex_fx_settings
        s.effect_type = "ABYSS_ROSE"; s.seed = 9147; s.arms = 14; s.rings = 3; s.segments = 128; s.radius = 3.45; s.inner_radius = .28
        s.thickness = .20; s.arc_thickness = .015; s.height = .55; s.turns = 1.45; s.swirl = 1.3; s.petal_amount = .95; s.noise = .78
        s.jaggedness = .38; s.sharpness = .52; s.taper = .75; s.add_core = True; s.add_arcs = True; s.add_sparks = True
        s.spark_count = 58; s.spark_size = .035; s.glow_power = 3.5; s.primary_color = (.08, .07, .10, .56); s.accent_color = (.47, .03, .92, .78); s.highlight_color = (.92, .97, 1, 1)
        return {'FINISHED'}


class VORTEXFX_PT_panel(bpy.types.Panel):
    bl_label = "Vortex FX Generator"
    bl_idname = "VORTEXFX_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VFX"
    def draw(self, context):
        layout = self.layout; s = context.scene.vortex_fx_settings
        col = layout.column(align=True); col.prop(s, "effect_type"); row = col.row(align=True); row.prop(s, "seed"); row.operator("vortexfx.randomize", text="Random", icon='FILE_REFRESH'); col.operator("vortexfx.preset_image_like", icon='SHADING_RENDERED')
        box = layout.box(); box.label(text="Structure"); grid = box.grid_flow(columns=2, align=True)
        for prop in ["arms", "rings", "segments", "radius", "inner_radius", "thickness", "arc_thickness", "height"]: grid.prop(s, prop)
        box = layout.box(); box.label(text="Motion / Shape"); grid = box.grid_flow(columns=2, align=True)
        for prop in ["turns", "swirl", "petal_amount", "noise", "jaggedness", "sharpness", "taper", "reverse", "alternate_direction"]: grid.prop(s, prop)
        box = layout.box(); box.label(text="Details"); box.prop(s, "add_core"); box.prop(s, "add_arcs"); box.prop(s, "add_sparks")
        if s.add_sparks:
            row = box.row(align=True); row.prop(s, "spark_count"); row.prop(s, "spark_size")
        box = layout.box(); box.label(text="Color / Glow"); box.prop(s, "glow_power"); box.prop(s, "primary_color"); box.prop(s, "accent_color"); box.prop(s, "highlight_color")
        box = layout.box(); box.label(text="Tilt / Animation"); row = box.row(align=True); row.prop(s, "tilt_x"); row.prop(s, "tilt_y"); box.prop(s, "roll_z"); box.prop(s, "animate")
        if s.animate:
            row = box.row(align=True); row.prop(s, "frame_start"); row.prop(s, "frame_end")
        layout.separator(); layout.prop(s, "auto_clear"); layout.operator("vortexfx.generate", text="Generate Vortex FX", icon='MOD_SPIRAL'); layout.operator("vortexfx.clear", text="Clear Generated", icon='TRASH')


classes = (VortexFXSettings, VORTEXFX_OT_generate, VORTEXFX_OT_randomize, VORTEXFX_OT_clear, VORTEXFX_OT_preset_image_like, VORTEXFX_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vortex_fx_settings = PointerProperty(type=VortexFXSettings)


def unregister():
    if hasattr(bpy.types.Scene, "vortex_fx_settings"):
        del bpy.types.Scene.vortex_fx_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
