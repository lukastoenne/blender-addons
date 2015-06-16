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
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import *
from mathutils import *
from distant_worlds.driver import *

# -----------------------------------------------------------------------------
# Properties

class DistantWorldsObject(PropertyGroup):
    identifier = StringProperty(name="Identifier",
                                description="Identifier of the body represented by the object",
                                options={'HIDDEN'})

    def draw(self, context, layout):
        pass

# -----------------------------------------------------------------------------
# Body Object

@body_driver_function
def get_body_location(body):
    if not body:
        return Vector((0,0,0))
    orbit = body.orbit_params
    return body.matrix_orbit_world  * orbit.location(orbit.current_time)

def body_object_poll(ob):
    if ob.type == 'MESH':
        return True
    return False

def body_object_verify(ob, body):
    if not body_object_poll(ob):
        return False

    make_body_driver(ob, "location", get_body_location, body)

# -----------------------------------------------------------------------------
# Path Object

@body_driver_function
def get_path_location(body):
    if not body:
        return Vector((0,0,0))
    parent = body.parent_body
    if parent:
        orbit = parent.orbit_params
        return orbit.location(orbit.current_time)
    else:
        return Vector((0,0,0))

def path_object_poll(ob):
    if ob.type == 'CURVE':
        return True
    return False

def path_ellipsis(body, eta):
    orbit = body.orbit_params
    x = orbit.semiminor * sin(eta)
    y = orbit.semimajor * cos(eta) - orbit.focus
    return Vector((x, -y, 0.0))

def path_tangent(body, eta):
    orbit = body.orbit_params
    dx = orbit.semiminor * cos(eta)
    dy = -orbit.semimajor * sin(eta)
    return Vector((dx, -dy, 0.0))

# calculates bezier curve approximation of an ellipse, based on
# http://www.spaceroots.org/documents/ellipse/node22.html
def path_bezier_segment(body, eta1, eta2):
    co1 = path_ellipsis(body, eta1)
    co2 = path_ellipsis(body, eta2)
    dco1 = path_tangent(body, eta1)
    dco2 = path_tangent(body, eta2)

    t = tan((eta2 - eta1) * 0.5)
    alpha = sin(eta2 - eta1) * (sqrt(4.0 + 3.0*t*t) - 1.0) / 3.0

    return co1, co2, co1 + alpha * dco1, co2 - alpha * dco2

def path_create_spline(spline, body):
    spline.type = 'BEZIER'
    spline.use_cyclic_u = True

    points = spline.bezier_points
    res = len(points)
    if res < 2:
        return

    delta = 2.0*pi / res
    for i in range(res):
        j = (i+1) % res
        p1 = points[i]
        p2 = points[j]
        eta1 = delta * i
        eta2 = delta * j

        p1.handle_right_type='FREE'
        p2.handle_left_type='FREE'
        p1.co, p2.co, p1.handle_right, p2.handle_left = path_bezier_segment(body, eta1, eta2)

def path_object_verify(ob, body):
    if not path_object_poll(ob):
        return False

    # init curve data
    orbit = body.orbit_params
    make_body_driver(ob, "location", get_path_location, body)

    curve = ob.data
    curve.dimensions = '2D'
    splines = curve.splines
    
    res = body.path_resolution

    if len(splines) != 1 or len(splines[0].bezier_points) > res:
        splines.clear()
        splines.new('BEZIER')
        splines.active = splines[0]

    num = len(splines[0].bezier_points)
    if res > num:
        splines[0].bezier_points.add(res - num)

    path_create_spline(splines[0], body)

    return True

# -----------------------------------------------------------------------------
# GUI

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

# -----------------------------------------------------------------------------
# Registration

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
