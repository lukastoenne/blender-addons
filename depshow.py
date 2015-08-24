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

bl_info = {
    "name": "Depshow",
    "author": "Lukas Toenne",
    "version": (0, 1, 0),
    "blender": (2, 7, 5),
    "location": "Scene Properties",
    "description": "Show dependency graph nodes via graphviz output",
    "warning": "",
    "category": "Community"}

import os, subprocess
import bpy
from bpy.types import Operator

dotfile = '/tmp/depsgraph.dot'
imgfile = '/tmp/depsgraph.png'
dotformat = 'png'

class DepshowOperator(Operator):
    bl_idname = "scene.depsgraph_show"
    bl_label = "Show Depsgraph"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene is not None and hasattr(scene, 'depsgraph') and hasattr(scene.depsgraph, 'debug_graphviz')

    def execute(self, context):
        scene = context.scene
        dg = scene.depsgraph
        
        dg.debug_graphviz(dotfile)
        
        process = subprocess.Popen(['dot', '-T'+dotformat, '-o', imgfile, dotfile])
        process.wait()
        
        subprocess.Popen(['xdg-open', imgfile])
        
        return {'FINISHED'}

def draw_depshow(self, context):
    layout = self.layout
    layout.operator("scene.depsgraph_show")

def register():
    bpy.utils.register_class(DepshowOperator)
    bpy.types.SCENE_PT_scene.append(draw_depshow)

def unregister():
    bpy.types.SCENE_PT_scene.remove(draw_depshow)
    bpy.utils.unregister_class(DepshowOperator)

if __name__ == "__main__":
    register()
