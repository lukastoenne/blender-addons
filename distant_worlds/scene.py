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
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.props import *
from distant_worlds.util import *
from distant_worlds.idmap import *
from distant_worlds.orbit import *
from distant_worlds.driver import *
from distant_worlds.objects import *

# -----------------------------------------------------------------------------
# Properties

class DistantWorldsBody(PropertyGroup, metaclass = DistantWorldsPropertyGroup):
    #orbit_params = PointerProperty(name="Orbital Parameters", type=DistantWorldsOrbitParams) # created in register()

    def verify_body_object(self):
        ob = self.body_object
        if  ob:
            body_object_verify(ob, self)

    def verify_path_object(self):
        ob = self.path_object
        if ob:
            path_object_verify(ob, self)

    def body_object_update(self, context):
        self.verify_body_object()
    body_object = IDRefProperty(name="Body Object",
                                description="Main object representing the body",
                                type='Object',
                                update=body_object_update,
                                poll=lambda _,x: body_object_poll(x),
                                )
    def path_object_update(self, context):
        self.verify_path_object()
    path_object = IDRefProperty(name="Path Object",
                                description="Curve object for the body's path",
                                type='Object',
                                update=path_object_update,
                                poll=lambda _,x: path_object_poll(x),
                                )
    path_resolution = IntProperty(name="Path Resolution",
                                  description="Number of path curve control points",
                                  default=16,
                                  min=3,
                                  soft_min=3,
                                  soft_max=64,
                                  update=path_object_update,
                                  )

    @property
    def dw(self):
        return self.id_data.distant_worlds

    def name_update(self, context):
        # modify id property directly, to avoid infinte update loop
        self['name'] = unique_name(self.dw.bodies, self)

    name = StringProperty(name="Name", description="Name of the body", update=name_update)

    def param_update(self, context):
        self.verify_body_object()
        self.verify_path_object()

    def draw(self, context, layout):
        # needed for escalating update calls back to the body
        layout.context_pointer_set("distant_worlds_body", self)

        layout.prop(self, "name")
        template_IDRef(layout, self, "body_object")
        template_IDRef(layout, self, "path_object")
        col = layout.column(align=True)
        col.enabled = bool(self.path_object)
        col.prop(self, "path_resolution")

        layout.separator()

        layout.label("Orbital Parameters:")
        self.orbit_params.draw(context, layout)

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

#    def apply_to_scene(self, scene):
#        pass

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "time_scale")
        col.prop(self, "time_exponent")

class DistantWorldsScene(PropertyGroup):
    #bodies = CollectionProperty(type=DistantWorldsBody) # created in register()
    active_body = IntProperty(name="Active Body", description="Index of the selected body", default=0)

    def add_body(self, name):
        body = self.bodies.add()
        body.name = name

    def remove_body(self, name):
        body = self.bodies.get(name, None)
        if body:
            self.bodies.remove(body)

    def draw_bodies(self, context, layout):
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("distant_worlds.load_default_bodies")
        layout.template_list("DISTANT_WORLDS_UL_bodies", "", self, "bodies", self, "active_body")

        layout.separator()

        if self.active_body >= 0 and self.active_body < len(self.bodies):
            act_body = self.bodies[self.active_body]
            act_body.draw(context, layout)

    #time = PointerProperty(type=DistantWorldsTimeSettings) # created in register()

    @property
    def current_scene_time(self):
        scene = self.id_data
        return scene.frame_current / scene.render.fps

    @property
    def current_sim_time(self):
        return self.current_scene_time * self.time.time_scale + self.time.epoch

class DistantWorldsBodiesUIList(UIList):
    bl_idname = "DISTANT_WORLDS_UL_bodies"
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", icon_value=icon, emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.label(icon_value=icon)

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

class DistantWorldsOperator_LoadDefaultBodies(bpy.types.Operator):
    """Load default Distant Worlds bodies setup"""
    bl_idname = "distant_worlds.load_default_bodies"
    bl_label = "Load Default Bodies"

    name = StringProperty(name="Name", description="Name of the body", default="Planet")

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.distant_worlds

    def execute(self, context):
        dw = context.scene.distant_worlds
        dw.add_body(self.name)
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# GUI

class DistantWorldsPanelSceneBodies(Panel):
    """Distant Worlds Bodies"""
    bl_label = "Distant Worlds Bodies"
    bl_idname = "distant_worlds.panel_bodies"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        dw = context.scene.distant_worlds
        if dw:
            dw.draw_bodies(context, self.layout)

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
    DistantWorldsBody.orbit_params = PointerProperty(name="Orbital Parameters",
                                                     type=DistantWorldsOrbitParams)

    bpy.utils.register_class(DistantWorldsBody)
    bpy.utils.register_class(DistantWorldsTimeSettings)

    DistantWorldsScene.bodies = CollectionProperty(type=DistantWorldsBody)
    DistantWorldsScene.time = PointerProperty(type=DistantWorldsTimeSettings)
    bpy.utils.register_class(DistantWorldsScene)
    
    bpy.types.Scene.distant_worlds = PointerProperty(name="Distant Worlds",
                                                     description="Settings for the Distant Worlds addon",
                                                     type=DistantWorldsScene)

    bpy.utils.register_class(DistantWorldsOperator_LoadDefaultBodies)
    bpy.utils.register_class(DistantWorldsBodiesUIList)
    bpy.utils.register_class(DistantWorldsPanelSceneBodies)
    bpy.utils.register_class(DistantWorldsPanelSceneTime)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOperator_LoadDefaultBodies)   
    bpy.utils.unregister_class(DistantWorldsBodiesUIList)
    bpy.utils.unregister_class(DistantWorldsPanelSceneBodies)
    bpy.utils.unregister_class(DistantWorldsPanelSceneTime)

    del bpy.types.Scene.distant_worlds

    bpy.utils.unregister_class(DistantWorldsScene)
    bpy.utils.unregister_class(DistantWorldsTimeSettings)
    bpy.utils.unregister_class(DistantWorldsBody)

if __name__ == "__main__":
    register()
