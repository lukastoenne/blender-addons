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
from bpy.props import EnumProperty

dotfile = '/tmp/depsgraph.dot'
imgfile = '/tmp/depsgraph.svg'
dotformat = 'svg'

def enum_property_copy(prop):
    items = [(i.identifier, i.name, i.description, i.icon, i.value) for i in prop.enum_items]
    return EnumProperty(name=prop.name,
                        description=prop.description,
                        default=prop.default,
                        items=items)

class DepshowOperator(Operator):
    bl_idname = "scene.depsgraph_show"
    bl_label = "Show Debug Graphviz Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    function_type = enum_property_copy(bpy.types.NodeTree.bl_rna.functions['bvm_debug_graphviz'].parameters['function_type'])
    debug_mode = enum_property_copy(bpy.types.NodeTree.bl_rna.functions['bvm_debug_graphviz'].parameters['debug_mode'])

    def execute(self, context):
        if hasattr(context, "debug_depsgraph"):
            scene = context.debug_depsgraph
            dg = scene.depsgraph
            dg.debug_graphviz(dotfile)
        elif hasattr(context, "debug_nodetree"):
            ntree = context.debug_nodetree
            ntree.bvm_debug_graphviz(dotfile, self.function_type, self.debug_mode, label=ntree.name)
        else:
            return {'CANCELLED'}
        
        process = subprocess.Popen(['dot', '-T'+dotformat, '-o', imgfile, dotfile])
        process.wait()
        
        subprocess.Popen(['xdg-open', imgfile])
        
        return {'FINISHED'}

def draw_depshow_op(layout, ntree):
    if isinstance(ntree, bpy.types.GeometryNodeTree):
        funtype = 'GEOMETRY'
    elif isinstance(ntree, bpy.types.InstancingNodeTree):
        funtype = 'INSTANCING'
    elif isinstance(ntree, bpy.types.TextureNodeTree):
        funtype = 'TEXTURE'
    elif isinstance(ntree, bpy.types.ForceFieldNodeTree):
        funtype = 'FORCEFIELD'
    else:
        return

    layout.context_pointer_set("debug_nodetree", ntree)

    col = layout.column(align=True)
    props = col.operator("scene.depsgraph_show", text="Nodes")
    props.function_type = funtype
    props.debug_mode = 'NODES'
    props = col.operator("scene.depsgraph_show", text="Nodes (unoptimized)")
    props.function_type = funtype
    props.debug_mode = 'NODES_UNOPTIMIZED'
    props = col.operator("scene.depsgraph_show", text="Code")
    props.function_type = funtype
    props.debug_mode = 'CODEGEN'

def draw_debug_depsgraph(self, context):
    scene = context.scene
    if hasattr(scene, 'depsgraph') and hasattr(scene.depsgraph, 'debug_graphviz'):
        layout = self.layout
        layout.context_pointer_set("debug_depsgraph", scene)
        draw_depshow_op(layout)

class NodeTreeDebugPanel(Panel):
    bl_idname = "nodes.bvm_debug_graphviz"
    bl_label = "Debug Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(cls, context):
        return context.space_data.edit_tree is not None

    def draw(self, context):
        space = context.space_data
        ntree = space.edit_tree
        if hasattr(ntree, 'bvm_debug_graphviz'):
            layout = self.layout
            draw_depshow_op(layout, ntree)

def register():
    bpy.utils.register_class(DepshowOperator)
    bpy.utils.register_class(NodeTreeDebugPanel)

def unregister():
    bpy.utils.unregister_class(NodeTreeDebugPanel)
    bpy.utils.unregister_class(DepshowOperator)

if __name__ == "__main__":
    register()
