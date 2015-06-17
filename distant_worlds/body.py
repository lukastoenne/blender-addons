
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

# -----------------------------------------------------------------------------
# Properties

class DistantWorldsComponent(metaclass = DistantWorldsPropertyGroup):
    def prop_update_verify(self, context):
        body = getattr(context, 'distant_worlds_body', None)
        if body:
            self.verify(body)

    enabled = BoolProperty(name="Enabled",
                           description="Use this component",
                           default=False,
                           update=prop_update_verify,
                           )


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

    #### Components ####

    #component_surface = PointerProperty(name="Surface Component", type=DistantWorldsComponentSurface)
    #component_path = PointerProperty(name="Path Component", type=DistantWorldsComponentPath)

    @property
    def components(self):
        attrs = ['component_surface', 'component_path']
        return { attr : getattr(self, attr) for attr in attrs }

    def verify_all(self):
        for comp in self.components.values():
            comp.verify(self)

    @property
    def used_objects(self):
        for comp in self.components.values():
            for ob in comp.used_objects:
                yield ob

    #### Parent Body ####

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

    #### Name ####

    def name_get(self):
        return self.get('name', "")
    def name_set(self, value):
        self['name'] = value
        self['name'] = unique_name(self.dw.bodies, self)
    name = StringProperty(name="Name", description="Name of the body", get=name_get, set=name_set)

    #### Serialization ####
    
    def write_preset_py(self, file_preset):
        props = ["component_path.resolution"]
        for p in props:
            file_preset.write("body.{prop} = {value}\n".format(prop=p, value=exec("self."+p)))
        
        # map to the new body instance uid
        parent = self.parent_body
        if parent:
            file_preset.write("body.parent_body_uid = body{uid}.uid\n".format(uid=parent.uid))

        file_preset.write("orbit = body.orbit_params\n")
        self.orbit_params.write_preset_py(file_preset)

    #### UI ####

    def param_update(self, context):
        self.verify_all()

    def draw(self, context, layout):
        # needed for escalating update calls back to the body
        layout.context_pointer_set("distant_worlds_body", self)

        layout.prop(self, "name", text="")

        layout.separator()

        layout.prop(self, "parent_body_enum")

        for comp in self.components.values():
            box = layout.box()
            box.prop(comp, "enabled", text=comp.bl_label)
            if comp.enabled:
                comp.draw(context, box)

        layout.separator()

        layout.label("Orbital Parameters:")
        self.orbit_params.draw(context, layout)


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


# -----------------------------------------------------------------------------
# Registration

def register():
    DistantWorldsBody.orbit_params = PointerProperty(name="Orbital Parameters",
                                                     type=DistantWorldsOrbitParams)
    DistantWorldsBody.component_surface = PointerProperty(name="Surface Component",
                                                          type=bpy.types.DistantWorldsComponentSurface)
    DistantWorldsBody.component_path = PointerProperty(name="Path Component",
                                                       type=bpy.types.DistantWorldsComponentPath)

    bpy.utils.register_class(DistantWorldsBody)

    bpy.utils.register_class(DistantWorldsBodiesUIList)

def unregister():
    bpy.utils.unregister_class(DistantWorldsBodiesUIList)

    bpy.utils.unregister_class(DistantWorldsBody)

if __name__ == "__main__":
    register()
