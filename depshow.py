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
from bpy.types import Operator, Panel
from bpy.props import BoolProperty

dotfile = '/tmp/depsgraph.dot'
imgfile = '/tmp/depsgraph.svg'
dotformat = 'svg'

class DepshowOperator(Operator):
    bl_idname = "scene.depsgraph_show"
    bl_label = "Show Debug Graphviz Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    finalize = BoolProperty(name="Finalize", default=True)

    def execute(self, context):
        
        if hasattr(context, "debug_depsgraph"):
            scene = context.debug_depsgraph
            dg = scene.depsgraph
            dg.debug_graphviz(dotfile)
        elif hasattr(context, "debug_texture"):
            tex = context.debug_texture
            tex.debug_nodes_graphviz(dotfile, self.finalize)
        elif hasattr(context, "debug_modifiers"):
            ob = context.debug_modifiers
            ob.debug_geometry_nodes_graphviz(dotfile, self.finalize)
        elif hasattr(context, "debug_duplis"):
            ob = context.debug_duplis
            ob.debug_instancing_nodes_graphviz(dotfile, self.finalize)
        else:
            return {'CANCELLED'}
        
        process = subprocess.Popen(['dot', '-T'+dotformat, '-o', imgfile, dotfile])
        process.wait()
        
        subprocess.Popen(['xdg-open', imgfile])
        
        return {'FINISHED'}

def draw_depshow_op(layout):
    col = layout.column(align=True)
    props = col.operator("scene.depsgraph_show")
    props.finalize = True
    props = col.operator("scene.depsgraph_show", text="(unoptimized)")
    props.finalize = False

def draw_debug_depsgraph(self, context):
    scene = context.scene
    if hasattr(scene, 'depsgraph') and hasattr(scene.depsgraph, 'debug_graphviz'):
        layout = self.layout
        layout.context_pointer_set("debug_depsgraph", scene)
        draw_depshow_op(layout)

def draw_debug_modifiers(self, context):
    ob = context.object
    if hasattr(ob, 'debug_geometry_nodes_graphviz'):
        layout = self.layout
        layout.context_pointer_set("debug_modifiers", ob)
        draw_depshow_op(layout)

def draw_debug_duplis(self, context):
    ob = context.object
    if hasattr(ob, 'debug_instancing_nodes_graphviz'):
        layout = self.layout
        layout.context_pointer_set("debug_duplis", ob)
        draw_depshow_op(layout)

class TextureDebugNodesPanel(Panel):
    bl_label = "Debug Nodes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        tex = context.texture
        return tex and (tex.type != 'NONE' or tex.use_nodes)

    def draw(self, context):
        tex = context.texture
        if hasattr(tex, 'debug_nodes_graphviz'):
            layout = self.layout
            layout.context_pointer_set("debug_texture", tex)
            draw_depshow_op(layout)

def register():
    bpy.utils.register_class(DepshowOperator)
    bpy.types.SCENE_PT_scene.append(draw_debug_depsgraph)
    bpy.types.DATA_PT_modifiers.append(draw_debug_modifiers)
    bpy.types.OBJECT_PT_duplication.append(draw_debug_duplis)
    bpy.utils.register_class(TextureDebugNodesPanel)

def unregister():
    bpy.types.SCENE_PT_scene.remove(draw_debug_depsgraph)
    bpy.types.DATA_PT_modifiers.remove(draw_debug_modifiers)
    bpy.types.OBJECT_PT_duplication.remove(draw_debug_duplis)
    bpy.utils.unregister_class(TextureDebugNodesPanel)
    bpy.utils.unregister_class(DepshowOperator)

if __name__ == "__main__":
    register()
