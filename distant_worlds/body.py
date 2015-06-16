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

    object_properties = {"body_object", "path_object"}
    @property
    def used_objects(self):
        for prop in self.object_properties:
            ob = getattr(self, prop, None)
            if ob:
                yield ob

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

    bpy.utils.register_class(DistantWorldsBody)

    bpy.utils.register_class(DistantWorldsBodiesUIList)

def unregister():
    bpy.utils.unregister_class(DistantWorldsBodiesUIList)

    bpy.utils.unregister_class(DistantWorldsBody)

if __name__ == "__main__":
    register()
