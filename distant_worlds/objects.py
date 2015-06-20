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
import bpy, bmesh
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import *
from bpy_extras.object_utils import object_data_add
from mathutils import *
from distant_worlds.body import DistantWorldsComponent
from distant_worlds.driver import *
from distant_worlds.util import *
from distant_worlds.idmap import *

# -----------------------------------------------------------------------------
# Properties

class DistantWorldsObject(PropertyGroup):
    identifier = StringProperty(name="Identifier",
                                description="Identifier of the body represented by the object",
                                options={'HIDDEN'})

    def draw(self, context, layout):
        pass

# -----------------------------------------------------------------------------
# Surface Object

@body_driver_function
def get_body_location(body):
    if not body:
        return Vector((0,0,0))
    orbit = body.orbit_params
    return body.matrix_orbit_world * orbit.location(orbit.current_time) * orbit.scale

@body_driver_function
def get_body_surface_rotation_qt(body):
    if not body:
        return Quaternion()
    orbit = body.orbit_params
    surface = body.component_surface
    mat = body.matrix_orbit_world * surface.matrix_equator_orbit
    return mat.to_quaternion()

@body_driver_function
def get_body_surface_rotation_euler(body):
    if not body:
        return Quaternion()
    orbit = body.orbit_params
    surface = body.component_surface
    mat = body.matrix_orbit_world * surface.matrix_equator_orbit
    return mat.to_euler('XYZ')

@body_driver_function
def get_body_surface_scale(body):
    if not body:
        return Vector((1,1,1))
    surface = body.component_surface
    return body.scale * surface.surface_scale

def surface_generate_sphere(ob, body, surface):
    mesh = ob.data

    bm = bmesh.new()
    #bm.from_mesh(mesh)

    subdiv = 2
    diameter = 2.0
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, diameter=diameter, matrix=Matrix.Identity(4))

    bm.to_mesh(mesh)
    bm.free()

class DistantWorldsComponentSurface(DistantWorldsComponent, PropertyGroup):
    bl_label = "Surface"

    radius = FloatProperty(name="Radius",
                           description="Radius at the equator",
                           default=1000.0,
                           soft_min=0.001,
                           soft_max=100000.0,
                           update=DistantWorldsComponent.prop_update_verify,
                           )

    oblateness = FloatProperty(name="Oblateness",
                               description="Ratio of equatorial bulge to radius",
                               default=0.0,
                               min=0.0,
                               soft_min=0.0,
                               soft_max=0.5,
                               update=DistantWorldsComponent.prop_update_verify,
                               )

    def object_poll(self, ob):
        if ob.type == 'MESH':
            return True
        return False
    object = IDRefProperty(name="Object",
                           description="Mesh object representing the surface",
                           type='Object',
                           poll=object_poll,
                           update=DistantWorldsComponent.prop_update_verify,
                           )

    @property
    def matrix_equator_orbit(self):
        # TODO
        mat = Matrix.Identity(4)
        return mat

    @property
    def surface_scale(self):
        return Vector((1.0, 1.0, 1 - self.oblateness)) * self.radius

    def draw(self, context, layout):
        template_IDRef(layout, self, "object")
        split = layout.split()
        col = split.column(align=True)
        col.prop(self, "radius")
        col.prop(self, "oblateness")

    def verify(self, body, create=False):
        ob = self.object
        if ob and not self.object_poll(ob):
            if create:
                self.object = None
                bpy.data.objects.remove(ob)
                ob = None
            else:
                return False
        if not ob:
            if create:
                mesh = bpy.data.meshes.new(name="{}.surface".format(body.name))
                # useful for development when the mesh may be invalid.
                # mesh.validate(verbose=True)
                base = object_data_add(bpy.context, mesh)
                ob = base.object
                self.object = ob
            else:
                return False

        make_body_driver(ob, "location", get_body_location, body)
        make_body_driver(ob, "rotation_quaternion", get_body_surface_rotation_qt, body)
        make_body_driver(ob, "rotation_euler", get_body_surface_rotation_euler, body)
        make_body_driver(ob, "scale", get_body_surface_scale, body)

        surface_generate_sphere(ob, body, self)

        return True

    @property
    def used_objects(self):
        ob = self.object
        if ob:
            yield ob

# -----------------------------------------------------------------------------
# Path Object

@body_driver_function
def get_path_location(body):
    if not body:
        return Vector((0,0,0))
    parent = body.parent_body
    if parent:
        orbit = parent.orbit_params
        return orbit.location(orbit.current_time) * orbit.scale
    else:
        return Vector((0,0,0))

@body_driver_function
def get_path_scale(body):
    if not body:
        return Vector((1,1,1))
    orbit = body.orbit_params
    scale = orbit.scale
    return Vector((scale, scale, scale))

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

def path_curve_generate(ob, body, path):
    # init curve data
    orbit = body.orbit_params
    make_body_driver(ob, "location", get_path_location, body)
    make_body_driver(ob, "scale", get_path_scale, body)

    curve = ob.data
    curve.dimensions = '2D'
    curve.fill_mode = 'NONE'
    splines = curve.splines
    
    res = path.resolution

    if len(splines) != 1 or len(splines[0].bezier_points) > res:
        splines.clear()
        splines.new('BEZIER')
        splines.active = splines[0]

    num = len(splines[0].bezier_points)
    if res > num:
        splines[0].bezier_points.add(res - num)

    path_create_spline(splines[0], body)

    return True

class DistantWorldsComponentPath(DistantWorldsComponent, PropertyGroup):
    bl_label = "Path"

    def object_poll(self, ob):
        if ob.type == 'CURVE':
            return True
        return False
    object = IDRefProperty(name="Path Object",
                           description="Curve object for the body's path",
                           type='Object',
                           poll=object_poll,
                           update=DistantWorldsComponent.prop_update_verify,
                           )
    resolution = IntProperty(name="Path Resolution",
                             description="Number of path curve control points",
                             default=16,
                             min=3,
                             soft_min=3,
                             soft_max=64,
                             update=DistantWorldsComponent.prop_update_verify,
                             )

    def draw(self, context, layout):
        template_IDRef(layout, self, "object")
        col = layout.column(align=True)
        col.enabled = bool(self.object)
        col.prop(self, "resolution")

    def verify(self, body, create=False):
        ob = self.object
        if ob and not self.object_poll(ob):
            if create:
                self.object = None
                bpy.data.objects.remove(ob)
                ob = None
            else:
                return False
        if not ob:
            if create:
                curve = bpy.data.curves.new(name="{}.path".format(body.name), type='CURVE')
                base = object_data_add(bpy.context, curve)
                ob = base.object
                self.object = ob
            else:
                return False

        path_curve_generate(ob, body, self)
        return True

    @property
    def used_objects(self):
        ob = self.object
        if ob:
            yield ob

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

    bpy.utils.register_class(DistantWorldsComponentSurface)
    bpy.utils.register_class(DistantWorldsComponentPath)

    bpy.utils.register_class(DistantWorldsObjectPanel)

def unregister():
    bpy.utils.unregister_class(DistantWorldsObjectPanel)

    bpy.utils.unregister_class(DistantWorldsComponentPath)
    bpy.utils.unregister_class(DistantWorldsComponentSurface)

    del bpy.types.Object.distant_worlds
    bpy.utils.unregister_class(DistantWorldsObject)

if __name__ == "__main__":
    register()
