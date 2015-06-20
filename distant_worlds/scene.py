### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

from math import *
import bpy
from bpy.types import Menu, Operator, Panel, PropertyGroup, UIList
from bpy.props import *
from bl_operators.presets import AddPresetBase
from distant_worlds.util import *
from distant_worlds.idmap import *
from distant_worlds.body import *

# -----------------------------------------------------------------------------
# Properties

class DistantWorldsTimeSettings(PropertyGroup):
    time_mode_items = [
        ('SECOND', 'Second', '1:1 (realtime)'),
        ('MINUTE', 'Minute', '60:1'),
        ('HOUR', 'Hour', '3600:1'),
        ('DAY_SOLAR', 'Day', '1 day/frame'),
        ('YEAR', 'Year', '1 year/frame'),
        ]

    # These settings map the scene time (in seconds) to the simulation time
    # Simulation time describes how fast objects move during playback or render
    #
    # To give access to a wider range of time scales, the primary scale setting is logarithmic.
    #
    #     t_sim = t_scene * 10^time_exponent + T0

    time_scale = FloatProperty(name="Time Scale",
                               description="Scale of the simulation time",
                               default=1.0,
                               min=1e-6,
                               max=1e9,
                               soft_min=1.0,
                               soft_max=1e3,
                               precision=5,
                               )

    def time_exponent_get(self):
        return log10(self.time_scale)
    # s = 10^q = (e^ln(10))^q = e^(ln(10)*q)
    def time_exponent_set(self, value):
        self.time_scale = exp(log(10.0) * value)
    _copy = lambda p, s: log10(p[1][s])
    time_exponent = FloatProperty(name="Time Scale Exponent",
                                  description="Exponential scale of the simulation time",
                                  default=_copy(time_scale, 'default'),
                                  min=_copy(time_scale, 'min'),
                                  max=_copy(time_scale, 'max'),
                                  soft_min=_copy(time_scale, 'soft_min'),
                                  soft_max=_copy(time_scale, 'soft_max'),
                                  precision=5,
                                  get=time_exponent_get,
                                  set=time_exponent_set,
                                  )

    epoch = FloatProperty(name="Epoch",
                          description="Origin of the simulation time at frame 0",
                          )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "time_scale")
        col.prop(self, "time_exponent")

# neat little trick to efficiently check for changed active object
# based on http://blender.stackexchange.com/a/31544
_scene_active_object_sync = None

class DistantWorldsScene(PropertyGroup):

    def param_update(self, context):
        for body in self.bodies:
            body.param_update(context)

    #### Observational Parameters ####
    scene_scale = FloatProperty(name="Scene Scale",
                                description="Scale of 1 BU (Blender scene unit) to 1 AU (distance Sun<->Earth)",
                                default=1.0,
                                min=1e-15,
                                max=1e15,
                                soft_min=0.001,
                                soft_max=1000.0,
                                update=param_update,
                                )

    body_scale = FloatProperty(name="Body Scale",
                               description="Scale of bodies relative to orbits",
                               default=1e9,
                               min=1e-15,
                               max=1e15,
                               soft_min=1,
                               soft_max=1e11,
                               update=param_update,
                               )

    def draw_params(self, context, layout):
        layout.prop(self, "scene_scale")
        layout.prop(self, "body_scale")

    #### Bodies Collection ####

    #bodies = CollectionProperty(type=DistantWorldsBody) # created in register()

    def active_body_index_update(self, context):
        scene = self.id_data
        act = scene.objects.active
        body = self.active_body
        if not body:
            return
        used_objects = [b for b in body.used_objects]
        if used_objects and act not in used_objects:
            scene.objects.active = used_objects[0]
    active_body_index = IntProperty(name="Active Body",
                                    description="Index of the selected body",
                                    default=0,
                                    update=active_body_index_update,
                                    )

    @property
    def active_body(self):
        if self.active_body_index >= 0 and self.active_body_index < len(self.bodies):
            return self.bodies[self.active_body_index]
        else:
            return None

    # Use the active object from the scene to activate associated bodies
    def sync_active_body(self):
        global _scene_active_object_sync

        scene = self.id_data
        act = scene.objects.active
        if act == _scene_active_object_sync:
            return
        _scene_active_object_sync = act

        for index, body in enumerate(self.bodies):
            if act in body.used_objects:
                self['active_body_index'] = index
                break

    def gen_body_uid(self):
        uid = self.get('bodies_uid', 0) + 1
        self['bodies_uid'] = uid
        return uid

    def add_body(self, name):
        body = self.bodies.add()
        body.name = name
        body.uid = self.gen_body_uid()
        return body

    def body_index(self, body):
        for i, b in enumerate(self.bodies):
            if b == body:
                return i
        return -1

    def remove_body(self, body):
        if body:
            index = self.body_index(body)
            self.bodies.remove(index)

            if index < self.active_body_index:
                self.active_body_index -= 1

    def clear_bodies(self):
        self.bodies.clear()

    def find_body_uid(self, uid):
        for body in self.bodies:
            if body.uid == uid:
                return body
        return None

    def get_sorted_body_indices(self):
        bodies = self.bodies
        num_bodies = len(bodies)

        parent_map = { body : [] for body in bodies }
        for index, body in enumerate(bodies):
            parent = body.parent_body
            if parent:
                parent_map[parent].append((body, index))
        
        def get_indices(parent, index):
            yield index
            for child, childindex in parent_map[parent]:
                for i in get_indices(child, childindex):
                    yield i

        index_map = []
        for index, root in enumerate(bodies):
            if not root.parent_body:
                for i in get_indices(root, index):
                    index_map.append(i)
        neworder = [0] * num_bodies
        for new, old in enumerate(index_map):
            neworder[old] = new

        return neworder

    def draw_bodies(self, context, layout):
        active_body = self.active_body

        row = layout.row()

        row.template_list("DISTANT_WORLDS_UL_bodies", "", self, "bodies", self, "active_body_index", rows=4)

        col = row.column(align=True)
        col.operator("distant_worlds.add_body", icon='ZOOMIN', text="")
        sub = col.column(align=True)
        sub.context_pointer_set("distant_worlds_body", active_body)
        sub.operator("distant_worlds.remove_body", icon='ZOOMOUT', text="")

        layout.separator()

        if active_body:
            active_body.draw(context, layout)

    #### Time Properties ####

    #time = PointerProperty(type=DistantWorldsTimeSettings) # created in register()

    @property
    def current_scene_time(self):
        scene = self.id_data
        return scene.frame_current / scene.render.fps

    @property
    def current_sim_time(self):
        return self.current_scene_time * self.time.time_scale + self.time.epoch

    #### Serialization ####

    def write_preset_py(self, file_preset):
        file_preset.write("dw.clear_bodies()\n")

        # we create all basic bodies first, so they can reference each other
        for body in self.bodies:
            file_preset.write("body{uid} = dw.add_body({name!r})\n".format(uid=body.uid, name=body.name))

        # now write all the properties
        for body in self.bodies:
            file_preset.write("body = body{uid}\n".format(uid=body.uid))
            body.write_preset_py(file_preset)
            file_preset.write("\n")


# -----------------------------------------------------------------------------
# Operators

'''
class DistantWorldsOperator_ApplyTimeSettings(bpy.types.Operator):
    """Apply time settings to the scene"""
    bl_idname = "distant_worlds.apply_time_settings"
    bl_label = "Apply Time Settings"

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.distant_worlds

    def execute(self, context):
        dw = context.scene.distant_worlds
        dw.time.apply_to_scene(context.scene)
        return {'FINISHED'}
'''

class DistantWorldsOperator_AddBody(bpy.types.Operator):
    """Add Distant Worlds body"""
    bl_idname = "distant_worlds.add_body"
    bl_label = "Add Body"

    name = StringProperty(name="Name", description="Name of the body", default="Planet")

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.distant_worlds

    def execute(self, context):
        dw = context.scene.distant_worlds
        dw.add_body(self.name)
        return {'FINISHED'}

class DistantWorldsOperator_RemoveBody(bpy.types.Operator):
    """Remove Distant Worlds body"""
    bl_idname = "distant_worlds.remove_body"
    bl_label = "Remove Body"

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.distant_worlds and \
               hasattr(context, "distant_worlds_body") and context.distant_worlds_body

    def execute(self, context):
        dw = context.scene.distant_worlds
        dw.remove_body(context.distant_worlds_body)
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Presets

class DistantWorldsPresetsMenu(Menu):
    bl_idname = "distant_worlds.presets_menu"
    bl_label = "Distant Worlds Presets"
    preset_subdir = "distant_worlds"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class DistantWorldsAddPreset(AddPresetBase, Operator):
    bl_idname = "distant_worlds.add_preset"
    bl_label = "Add Distant Worlds Preset"
    preset_subdir = "distant_worlds"
    preset_menu = "distant_worlds.presets_menu"

    preset_defines = [
        "scene = bpy.context.scene",
        "dw = scene.distant_worlds",
    ]

    preset_values = []

    # our own version of write_preset_py, adding a print call
    def write_preset_py(self, file_preset):
        scene = bpy.context.scene
        dw = scene.distant_worlds

        # call the original implementation to serialize preset_values
        AddPresetBase.write_preset_py(self, file_preset)

        dw.write_preset_py(file_preset)

# -----------------------------------------------------------------------------
# GUI

class DistantWorldsPanelSceneParams(Panel):
    """Distant Worlds Parameters"""
    bl_label = "Distant Worlds Parameters"
    bl_idname = "distant_worlds.panel_params"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        dw = context.scene.distant_worlds
        if dw:
            dw.draw_params(context, layout)

class DistantWorldsPanelSceneBodies(Panel):
    """Distant Worlds Bodies"""
    bl_label = "Distant Worlds Bodies"
    bl_idname = "distant_worlds.panel_bodies"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        row = layout.row().split()
        sub = row.row(align=True).split(align=True, percentage=0.75)
        sub.menu("distant_worlds.presets_menu", text=DistantWorldsPresetsMenu.bl_label)
        sub.operator("distant_worlds.add_preset", text="", icon='ZOOMIN')
        sub.operator("distant_worlds.add_preset", text="", icon='ZOOMOUT').remove_active = True

        layout.separator()

        dw = context.scene.distant_worlds
        if dw:
            dw.draw_bodies(context, layout)

class DistantWorldsPanelSceneTime(Panel):
    """Distant Worlds Time"""
    bl_label = "Distant Worlds Time"
    bl_idname = "distant_worlds.panel_time"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        dw = context.scene.distant_worlds
        if dw:
            dw.time.draw(context, self.layout)

# -----------------------------------------------------------------------------
# Registration

def register():
    bpy.utils.register_class(DistantWorldsTimeSettings)

    DistantWorldsScene.bodies = CollectionProperty(type=DistantWorldsBody)
    DistantWorldsScene.time = PointerProperty(type=DistantWorldsTimeSettings)
    bpy.utils.register_class(DistantWorldsScene)
    
    bpy.types.Scene.distant_worlds = PointerProperty(name="Distant Worlds",
                                                     description="Settings for the Distant Worlds addon",
                                                     type=DistantWorldsScene)

    bpy.utils.register_class(DistantWorldsOperator_AddBody)
    bpy.utils.register_class(DistantWorldsOperator_RemoveBody)
    bpy.utils.register_class(DistantWorldsPresetsMenu)
    bpy.utils.register_class(DistantWorldsAddPreset)
    bpy.utils.register_class(DistantWorldsPanelSceneParams)
    bpy.utils.register_class(DistantWorldsPanelSceneBodies)
    bpy.utils.register_class(DistantWorldsPanelSceneTime)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOperator_AddBody)   
    bpy.utils.unregister_class(DistantWorldsOperator_RemoveBody)
    bpy.utils.unregister_class(DistantWorldsAddPreset)
    bpy.utils.unregister_class(DistantWorldsPresetsMenu)
    bpy.utils.unregister_class(DistantWorldsPanelSceneParams)
    bpy.utils.unregister_class(DistantWorldsPanelSceneBodies)
    bpy.utils.unregister_class(DistantWorldsPanelSceneTime)

    del bpy.types.Scene.distant_worlds

    bpy.utils.unregister_class(DistantWorldsScene)
    bpy.utils.unregister_class(DistantWorldsTimeSettings)

if __name__ == "__main__":
    register()
