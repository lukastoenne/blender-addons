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

import bpy
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy.props import *
from distant_worlds.util import *
from distant_worlds.idmap import *

class DistantWorldsBody(PropertyGroup, metaclass = DistantWorldsPropertyGroup):
    body_object = IDRefProperty(name="Body Object", description="Main object representing the body", type='Object')
    path_object = IDRefProperty(name="Path Object", description="Curve object for the body's path", type='Object')

    @property
    def dw(self):
        return self.id_data.distant_worlds

    def name_update(self, context):
        self['name'] = unique_name(self.dw.bodies, self)

    name = StringProperty(name="Name", description="Name of the body", update=name_update)

    def draw(self, context, layout):
        layout.prop(self, "name")
        layout.prop(self, "body_object__enum", text="Object")
        layout.prop(self, "path_object__enum", text="Path Object")

class DistantWorldsScene(PropertyGroup):
    active_body = IntProperty(name="Active Body", description="Index of the selected body", default=0)

    def add_body(self, name):
        body = self.bodies.add()
        body.name = name

    def remove_body(self, name):
        body = self.bodies.get(name, None)
        if body:
            self.bodies.remove(body)

    def draw(self, context, layout):
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("distant_worlds.simple_operator")
        layout.template_list("DISTANT_WORLDS_UL_bodies", "", self, "bodies", self, "active_body")

        layout.separator()

        if self.active_body >= 0 and self.active_body < len(self.bodies):
            act_body = self.bodies[self.active_body]
            act_body.draw(context, layout)

class DistantWorldsBodiesUIList(UIList):
    bl_idname = "DISTANT_WORLDS_UL_bodies"
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", icon_value=icon, emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.label(icon_value=icon)

class DistantWorldsOperator_LoadDefault(bpy.types.Operator):
    """Load Default"""
    bl_idname = "distant_worlds.simple_operator"
    bl_label = "Load Solar System"

    name = StringProperty(name="Name", description="Name of the body", default="Planet")

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.distant_worlds

    def execute(self, context):
        dw = context.scene.distant_worlds
        dw.add_body(self.name)
        return {'FINISHED'}

class DistantWorldsScenePanel(Panel):
    """Distant Worlds Panel"""
    bl_label = "Distant Worlds"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        if context.scene.distant_worlds:
            context.scene.distant_worlds.draw(context, self.layout)

def register():
    bpy.utils.register_class(DistantWorldsBody)

    DistantWorldsScene.bodies = CollectionProperty(type=DistantWorldsBody)
    bpy.utils.register_class(DistantWorldsScene)
    
    bpy.types.Scene.distant_worlds = PointerProperty(name="Distant Worlds",
                                                     description="Settings for the Distant Worlds addon",
                                                     type=DistantWorldsScene)

    bpy.utils.register_class(DistantWorldsOperator_LoadDefault)
    bpy.utils.register_class(DistantWorldsBodiesUIList)
    bpy.utils.register_class(DistantWorldsScenePanel)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOperator_LoadDefault)   
    bpy.utils.unregister_class(DistantWorldsBodiesUIList)
    bpy.utils.unregister_class(DistantWorldsScenePanel)

    del bpy.types.Scene.distant_worlds

    bpy.utils.unregister_class(DistantWorldsScene)
    bpy.utils.unregister_class(DistantWorldsBody)

if __name__ == "__main__":
    register()
