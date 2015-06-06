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
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import *

class DistantWorldsObject(PropertyGroup):
    identifier = StringProperty(name="Identifier",
                                description="Identifier of the body represented by the object",
                                options={'HIDDEN'})

    def draw(self, context, layout):
        pass

class DistantWorldsObjectPanel(Panel):
    """Distant Worlds Panel"""
    bl_label = "Distant Worlds"
    bl_idname = "OBJECT_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        if context.object.distant_worlds:
            context.object.distant_worlds.draw(context, self.layout)

def register():
    bpy.utils.register_class(DistantWorldsObject)
    bpy.types.Object.distant_worlds = PointerProperty(name="Distant Worlds",
                                                      description="Settings for the Distant Worlds addon",
                                                      type=DistantWorldsObject)

    bpy.utils.register_class(DistantWorldsObjectPanel)

def unregister():
    bpy.utils.unregister_class(DistantWorldsObjectPanel)

    del bpy.types.Object.distant_worlds
    bpy.utils.unregister_class(DistantWorldsObject)

if __name__ == "__main__":
    register()
