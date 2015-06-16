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
    @property
    def dw(self):
        return self.id_data.distant_worlds

    uid = IntProperty(name="Unique Identifier",
                      min=0,
                      options={'HIDDEN'},
                      )

    #orbit_params = PointerProperty(name="Orbital Parameters", type=DistantWorldsOrbitParams) # created in register()

    @property
    def matrix_refplane_world(self):
        # apply additional transform based on parent bodies (for moons) and observational point
        parent = self.parent_body
        if parent:
            parent_orbit = parent.orbit_params
            return Matrix.Translation(parent_orbit.location(parent_orbit.current_time))
        else:
            return Matrix.Identity(4)

    @property
    def matrix_orbit_world(self):
        return self.matrix_refplane_world * self.orbit_params.matrix_orbit_refplane

    @property
    def matrix_equator_world(self):
        return self.matrix_refplane_world * self.orbit_params.matrix_equator_refplane

    def verify_body_object(self):
        ob = self.body_object
        if  ob:
            body_object_verify(ob, self)

    def verify_path_object(self):
        ob = self.path_object
        if ob:
            path_object_verify(ob, self)

    def verify_all(self):
        self.verify_body_object()
        self.verify_path_object()

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

    def parent_body_uid_update(self, context):
        self.verify_all()
    parent_body_uid = IntProperty(name="Parent Body UID",
                                  description="Unique identifier of the parent body",
                                  default=0,
                                  update=parent_body_uid_update,
                                  )
    @property
    def parent_body(self):
        return self.dw.find_body_uid(self.parent_body_uid)

    @property
    def ancestors(self):
        parent = self.parent_body
        while parent:
            yield parent
            parent = parent.parent_body

    @property
    def descendants(self):
        found = {self}
        visited = {self}
        def visit(body):
            visited.add(body)
            
            parent = body.parent_body
            if parent:
                if parent not in visited:
                    visit(parent)
                if parent in found:
                    found.add(body)

        for body in self.dw.bodies:
            if body not in visited:
                visit(body)
        found.remove(self)
        return found

    def body_enum_items(self, bodies=None, allow_null=False):
        if bodies is None:
            bodies = self.dw.bodies
        items = []
        if allow_null:
            items.append( ('0', "", "", 'NONE', 0) )
        for body in bodies:
            items.append( (str(body.uid), body.name, "", 'NONE', body.uid) )
        return items

    def parent_body_enum_items(self, context):
        bodies = set(self.dw.bodies) - {self} - self.descendants
        return self.body_enum_items(bodies, allow_null=True)
    def parent_body_enum_get(self):
        return self.parent_body_uid
    def parent_body_enum_set(self, value):
        self.parent_body_uid = value
    parent_body_enum = EnumProperty(name="Parent Body",
                                    description="Primary gravitational influence",
                                    items=parent_body_enum_items,
                                    get=parent_body_enum_get,
                                    set=parent_body_enum_set,
                                    )

    def name_get(self):
        return self.get('name', "")
    def name_set(self, value):
        self['name'] = value
        self['name'] = unique_name(self.dw.bodies, self)
    name = StringProperty(name="Name", description="Name of the body", get=name_get, set=name_set)

    def param_update(self, context):
        self.verify_all()

    def draw(self, context, layout):
        # needed for escalating update calls back to the body
        layout.context_pointer_set("distant_worlds_body", self)

        layout.prop(self, "name", text="")

        layout.separator()

        layout.prop(self, "parent_body_enum")

        layout.label("Objects:")
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

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "time_scale")
        col.prop(self, "time_exponent")

class DistantWorldsScene(PropertyGroup):
    #bodies = CollectionProperty(type=DistantWorldsBody) # created in register()
    active_body_index = IntProperty(name="Active Body", description="Index of the selected body", default=0)

    @property
    def active_body(self):
        if self.active_body_index >= 0 and self.active_body_index < len(self.bodies):
            return self.bodies[self.active_body_index]
        else:
            return None

    def gen_body_uid(self):
        uid = self.get('bodies_uid', 0) + 1
        self['bodies_uid'] = uid
        return uid

    def add_body(self, name):
        body = self.bodies.add()
        body.name = name
        body.uid = self.gen_body_uid()

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
            for parent in item.ancestors:
                layout.separator()

            layout.prop(item, "name", text="", icon_value=icon, emboss=False)
        
        elif self.layout_type in {'GRID'}:
            layout.label(icon_value=icon)

    def filter_items(self, context, data, prop):
        neworder = data.get_sorted_body_indices()
        return [], neworder


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

    bpy.utils.register_class(DistantWorldsOperator_AddBody)
    bpy.utils.register_class(DistantWorldsOperator_RemoveBody)
    bpy.utils.register_class(DistantWorldsBodiesUIList)
    bpy.utils.register_class(DistantWorldsPanelSceneBodies)
    bpy.utils.register_class(DistantWorldsPanelSceneTime)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOperator_AddBody)   
    bpy.utils.unregister_class(DistantWorldsOperator_RemoveBody)
    bpy.utils.unregister_class(DistantWorldsBodiesUIList)
    bpy.utils.unregister_class(DistantWorldsPanelSceneBodies)
    bpy.utils.unregister_class(DistantWorldsPanelSceneTime)

    del bpy.types.Scene.distant_worlds

    bpy.utils.unregister_class(DistantWorldsScene)
    bpy.utils.unregister_class(DistantWorldsTimeSettings)
    bpy.utils.unregister_class(DistantWorldsBody)

if __name__ == "__main__":
    register()
