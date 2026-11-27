"""blender_bridge.py — Version-safe helpers for Tier-2 offline Blender (`bpy`) studio & audio-reactive renders.

Import inside a script executed via:
    blender --background --python build_scene.py -- --out out/frames/frame_

Compatible across Blender 3.6 LTS, 4.0–4.5 LTS, and 5.0+ (handles EEVEE / EEVEE_NEXT enum changes,
Principled BSDF 4.0 socket renames, AgX / Filmic color transforms, and 4.2+ Compositor Glare bloom).
Note: `bpy` and `mathutils` are imported lazily inside functions so `doctor.mjs` syntax checks work anywhere.
"""
import json
import math
from pathlib import Path


def reset_scene(width=1920, height=1080, fps=30, frame_start=1, frame_end=180):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.fps = int(fps)
    scene.frame_start = int(frame_start)
    scene.frame_end = int(frame_end)
    return scene


def pick_engine(scene, prefer="EEVEE", samples=64, device="AUTO"):
    """Select EEVEE (3.6/4.2+/5.0 safe) or CYCLES with version-agnostic sampling."""
    import bpy
    valid = {e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items}
    if prefer.upper() == "CYCLES" and "CYCLES" in valid:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = int(samples)
        if hasattr(scene.cycles, "use_denoising"):
            scene.cycles.use_denoising = True
        if device.upper() in ("GPU", "AUTO"):
            try:
                prefs = bpy.context.preferences.addons["cycles"].preferences
                for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                    try:
                        prefs.compute_device_type = backend
                        prefs.get_devices()
                        if any(d.type == backend for d in prefs.devices):
                            for d in prefs.devices:
                                d.use = True
                            scene.cycles.device = "GPU"
                            break
                    except Exception:
                        continue
            except Exception:
                scene.cycles.device = "CPU"
        else:
            scene.cycles.device = "CPU"
    else:
        scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in valid else "BLENDER_EEVEE"
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = int(samples)
    return scene.render.engine


def setup_color_and_bloom(scene, exposure=0.0, prefer_view="AgX", look="None", bloom=True, threshold=0.88, intensity=0.08):
    """Configure AgX/Filmic color management and EEVEE/Compositor bloom across Blender 3.x–5.x."""
    views = {e.identifier for e in scene.view_settings.bl_rna.properties["view_transform"].enum_items}
    scene.view_settings.view_transform = prefer_view if prefer_view in views else ("AgX" if "AgX" in views else "Filmic")
    scene.view_settings.exposure = float(exposure)
    if look and look != "None":
        looks = {e.identifier for e in scene.view_settings.bl_rna.properties["look"].enum_items}
        if look in looks:
            scene.view_settings.look = look

    if not bloom:
        return
    if hasattr(scene.eevee, "use_bloom"):
        scene.eevee.use_bloom = True
        scene.eevee.bloom_threshold = float(threshold)
        scene.eevee.bloom_intensity = float(intensity)
        return

    # Blender 4.2+: EEVEE bloom lives in the Compositor Glare node
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    rl = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare_types = {e.identifier for e in glare.bl_rna.properties["glare_type"].enum_items}
    glare.glare_type = "BLOOM" if "BLOOM" in glare_types else "FOG_GLOW"
    if hasattr(glare, "threshold"):
        glare.threshold = float(threshold)
    if hasattr(glare, "mix"):
        glare.mix = 0.0
    if hasattr(glare, "size"):
        glare.size = 7
    comp = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], comp.inputs["Image"])


_BSDF_ALIASES = {
    "base_color": ("Base Color",),
    "metallic": ("Metallic",),
    "roughness": ("Roughness",),
    "ior": ("IOR",),
    "alpha": ("Alpha",),
    "transmission": ("Transmission Weight", "Transmission"),
    "coat": ("Coat Weight", "Clearcoat"),
    "coat_roughness": ("Coat Roughness", "Clearcoat Roughness"),
    "specular": ("Specular IOR Level", "Specular"),
    "emission": ("Emission Color", "Emission"),
    "emission_strength": ("Emission Strength",),
    "subsurface": ("Subsurface Weight", "Subsurface"),
    "sheen": ("Sheen Weight", "Sheen"),
}


def make_pbr_material(name, **props):
    """Create a Principled BSDF material mapping friendly keys safely across Blender 3.x and 4.x+."""
    import bpy
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return mat
    for key, val in props.items():
        candidates = _BSDF_ALIASES.get(key, (key,))
        for sock_name in candidates:
            if sock_name in bsdf.inputs:
                sock = bsdf.inputs[sock_name]
                if len( getattr(sock, "default_value", ()) ) == 4 and isinstance(val, (tuple, list)) and len(val) == 3:
                    val = (val[0], val[1], val[2], 1.0)
                sock.default_value = val
                break
    return mat


def build_cyclorama(size=22.0, height=12.0, bend_radius=2.6, color=(0.035, 0.04, 0.055, 1.0), roughness=0.78):
    """Create a curved L-shaped studio infinity backdrop so hero subjects sit in a grounded lit space."""
    import bpy
    import bmesh
    mesh = bpy.data.meshes.new("CycloramaMesh")
    obj = bpy.data.objects.new("Studio_Cyclorama", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    half = size * 0.5
    segs = 14
    rows = []
    # Front floor edge -> start of bend -> quarter-circle bend -> top of back wall
    pts_yz = [(-half, 0.0)]
    for i in range(segs + 1):
        ang = (i / segs) * (math.pi * 0.5)
        y = half - bend_radius + math.sin(ang) * bend_radius
        z = bend_radius - math.cos(ang) * bend_radius
        pts_yz.append((y, z))
    pts_yz.append((half, height))
    for y, z in pts_yz:
        v_left = bm.verts.new((-half, y, z))
        v_right = bm.verts.new((half, y, z))
        rows.append((v_left, v_right))
    for (a0, a1), (b0, b1) in zip(rows[:-1], rows[1:]):
        bm.faces.new((a0, a1, b1, b0))
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(make_pbr_material("Mat_Cyclorama", base_color=color, roughness=roughness, metallic=0.0))
    return obj


def add_area_lights(rig):
    """Add aimed AREA lights: rig = [{'name', 'pos':(x,y,z), 'target':(0,0,1), 'energy':800, 'color':(1,1,1), 'size':3.0}]."""
    import bpy
    from mathutils import Vector
    lights = []
    for spec in rig:
        bpy.ops.object.light_add(type="AREA", location=spec.get("pos", (4.0, -4.0, 5.0)))
        lt = bpy.context.active_object
        lt.name = spec.get("name", "StudioLight")
        lt.data.energy = float(spec.get("energy", 600.0))
        lt.data.color = tuple(spec.get("color", (1.0, 1.0, 1.0))[:3])
        lt.data.size = float(spec.get("size", 3.0))
        tgt = Vector(spec.get("target", (0.0, 0.0, 0.8)))
        direction = tgt - lt.location
        lt.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        lights.append(lt)
    return lights


def sample_songmap_frames(songmap_path, fps=30, duration=None, offset=0.0, kick_decay=0.22):
    """Sample `songmap.json` onto Blender integer frames (1..N), returning [{'frame', 't', 'kick', 'energy'}, ...]."""
    data = json.loads(Path(songmap_path).read_text(encoding="utf-8"))
    fallback_dur = (data.get("beats") or [6.0])[-1]
    dur = float(duration if duration is not None else data.get("duration", fallback_dur) - offset)
    n_frames = max(1, int(round(dur * fps)))
    env = data.get("env") or {"fps": fps, "rms": [0.5]}
    env_fps = float(env.get("fps", fps))
    rms = env.get("rms") or [0.5]
    low_hits = (data.get("accents") or {}).get("low") or (data.get("hits") or {}).get("low") or []

    out = []
    for f in range(1, n_frames + 1):
        t_song = offset + (f - 1) / fps
        idx = min(max(0.0, t_song * env_fps), len(rms) - 1)
        i0 = int(idx)
        frac = idx - i0
        energy = rms[i0] * (1 - frac) + rms[min(i0 + 1, len(rms) - 1)] * frac
        kick = 0.0
        for h in low_hits:
            ht = h[0] if isinstance(h, list) else h
            hs = h[1] if isinstance(h, list) else 1.0
            if ht <= t_song:
                kick = max(kick, hs * math.exp(-(t_song - ht) / max(1e-3, kick_decay) * 3.0))
        out.append({"frame": f, "t": round((f - 1) / fps, 4), "song_t": round(t_song, 4), "energy": energy, "kick": kick})
    return out
