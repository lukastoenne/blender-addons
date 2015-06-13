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
from mathutils import *
from distant_worlds.util import *

class driver_namespace(type):
    pass

def body_driver_function(func):
    def driver_func(body_name, *args, **kw):
        body = None
        scene = bpy.context.scene
        if scene:
            dw = scene.distant_worlds
            if dw:
                body = dw.bodies.get(body_name, None)
        
        return func(body, *args, **kw)

    name = funcname(func)
    if not hasattr(driver_namespace, name):
        print("Registering driver function '{}'".format(name))
        setattr(driver_namespace, name, driver_func)

    return func


def make_body_driver(data, prop, func, body):
    fcurves = data.driver_add(prop)
    if is_sequence(fcurves):
        indices = [i for i,v in enumerate(fcurves)]
    else:
        # driver_add returns single fcurve for scalars, treat it the same
        fcurves = [fcurves]
        indices = [-1]

    for fcurve, index in zip(fcurves, indices):
        drv = fcurve.driver
        drv.type = 'SCRIPTED'
        #drv.show_debug_info = True
        #print(bpy.app.driver_namespace['distant_worlds'])
        if index < 0:
            drv.expression = "distant_worlds.{}({!r})".format(funcname(func), body.name)
        else:
            #drv.expression = "exec('print(globals())')"
            drv.expression = "distant_worlds.{}({!r})[{}]".format(funcname(func), body.name, index)
 
    #var = drv.variables.new()
    #var.name = 'x'
    #var.type = 'TRANSFORMS'
 
#    targ = var.targets[0]
#    targ.id = rig
#    targ.transform_type = 'LOC_X'
#    targ.bone_target = 'Driver'
#    targ.use_local_space_transform = True
