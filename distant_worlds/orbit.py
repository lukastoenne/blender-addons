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
from bpy.types import PropertyGroup
from bpy.props import *
from mathutils import *

def newton_raphson(f, df, x0, epsilon, maxiter=100):
    x = x0
    y = f(x)
    dy = df(x)
    i = 0
    while abs(y) > epsilon and dy != 0.0 and i < maxiter:
        x = x - y / dy
        y = f(x)
        dy = df(x)
    return x

def debug_object_angle(name, angle, loc=Vector((0,0,0))):
    ob = bpy.data.objects.get(name, None)
    if not ob:
        return
    #print("DEBUG %s is %f" % (ob.name, angle))
    mloc, mrot, mscale = ob.matrix_world.decompose()
    mscale_mat = Matrix.Identity(4)
    mscale_mat[0][0] = mscale[0]
    mscale_mat[1][1] = mscale[1]
    mscale_mat[2][2] = mscale[2]
    ob.matrix_world =   Matrix.Translation(Vector(loc)) \
                      * Matrix.Rotation(angle, 4, 'Z') \
                      * Matrix.Rotation(radians(90.0), 4, 'X') \
                      * mscale_mat

def debug_object_scale(name, scale):
    ob = bpy.data.objects.get(name, None)
    if not ob:
        return
    mloc, mrot, mscale = ob.matrix_world.decompose()
    ob.matrix_world =   Matrix.Translation(mloc) \
                      * mrot.to_matrix().to_4x4() \
                      * Matrix.Scale(scale, 4)

class DistantWorldsEllipticalOrbit(PropertyGroup):
    @property
    def dw(self):
        return self.id_data.distant_worlds

    def param_update(self, context):
        body = getattr(context, "distant_worlds_body", None)
        if body:
            body.param_update(context)

    semimajor = FloatProperty(name="Semimajor Axis",
                              description="Length of the semimajor axis",
                              default=1.0,
                              min=0.0,
                              soft_min=0.01,
                              soft_max=1000000.0,
                              update=param_update,
                              )

    eccentricity = FloatProperty(name="Eccentricity",
                                 description="Elongation of the elliptic orbit",
                                 default=0.0,
                                 min=0.0,
                                 max=0.999999999,
                                 soft_min=0.0,
                                 soft_max=0.9,
                                 update=param_update,
                                 )

    inclination = FloatProperty(name="Inclination",
                                description="Vertical tilt of the path",
                                subtype='ANGLE',
                                default=radians(0.0),
                                min=radians(-90.0),
                                max=radians(+90.0),
                                soft_min=radians(-90.0),
                                soft_max=radians(+90.0),
                                update=param_update,
                                )

    ascending_node = FloatProperty(name="Ascending Node",
                                   description="Longitude of the ascending node",
                                   subtype='ANGLE',
                                   default=radians(0.0),
                                   soft_min=radians(-180.0),
                                   soft_max=radians(+180.0),
                                   update=param_update,
                                   )

    periapsis_argument = FloatProperty(name="Argument of the Periapsis",
                                       description="Orientation of the path in the orbital plane",
                                       subtype='ANGLE',
                                       default=radians(0.0),
                                       soft_min=radians(-180.0),
                                       soft_max=radians(+180.0),
                                       update=param_update,
                                       )

    use_orbital_plane = BoolProperty(name="Use Orbital Plane",
                                     description="Use path rotation out of the reference plane",
                                     default=True,
                                     update=param_update
                                     )

    # mean anomaly at epoch
    mean_anomaly_epoch = FloatProperty(name="Mean Anomaly at Epoch",
                                       description="Mean anomaly at the reference time",
                                       default=radians(0.0),
                                       soft_min=radians(-180.0),
                                       soft_max=radians(+180.0),
                                       update=param_update,
                                       )

    mean_motion = FloatProperty(name="Mean Motion",
                                description="Mean motion in radians per unit time",
                                default=radians(360.0),
                                update=param_update,
                                )

    @property
    def matrix_orbit_refplane(self):
        """Transformation from the orbital plane to the reference plane"""
        if self.use_orbital_plane:
            mat_w = Matrix.Rotation(self.periapsis_argument, 3, 'Z')
            mat_i = Matrix.Rotation(self.inclination, 3, 'X')
            mat_a = Matrix.Rotation(self.ascending_node, 3, 'Z')
            return (mat_a * mat_i * mat_w).to_4x4()
        else:
            return Matrix.Identity(4)

    @property
    def focus(self):
        return self.semimajor * self.eccentricity

    @property
    def semiminor(self):
        e = self.eccentricity
        return self.semimajor * sqrt(1.0 - e*e)

    def mean_anomaly(self, time):
        M = time * self.mean_motion + self.mean_anomaly_epoch
        debug_object_angle("mean_anomaly", M, Vector((0,self.focus,0)))
        return M

    def eccentric_anomaly(self, time):
        # use a Newton-Raphson solver to solve Kepler's equation:
        # M = E - e*sin(E)

        M = self.mean_anomaly(time)
        e = self.eccentricity

        f = lambda E: E - e * sin(E) - M
        df = lambda E: 1.0 - e * cos(E)

        E = newton_raphson(f, df, M, radians(0.1))
        debug_object_angle("eccentric_anomaly", E, Vector((0,self.focus,0)))
        return E

    def true_anomaly(self, time):
        E = self.eccentric_anomaly(time)
        e = self.eccentricity
        v = 2.0 * atan2(sqrt(1.0 + e) * sin(E * 0.5), sqrt(1.0 - e) * cos(E * 0.5))
        debug_object_angle("true_anomaly", v)
        return v

    def distance(self, time):
        e = self.eccentricity
        v = self.true_anomaly(time)
        d = self.semimajor * (1.0 - e*e) / (1.0 + e * cos(v))
        debug_object_scale("true_anomaly", d)
        return d

    def location(self, time):
        v = self.true_anomaly(time)
        r = self.distance(time)
        p = Vector(( sin(v), -cos(v), 0 )) * r
        return p

    def path_segments(self, res):
        a = self.semimajor
        b = self.semiminor
        f = self.focus

        def path_point(eta):
            x = b * sin(eta)
            y = a * cos(eta) - f
            dx = b * cos(eta)
            dy = -a * sin(eta)
            return Vector((x, -y, 0.0)), Vector((dx, -dy, 0.0))

        # calculates bezier curve approximation of an ellipse, based on
        # http://www.spaceroots.org/documents/ellipse/node22.html
        delta = 2.0*pi / res
        for i in range(res):
            j = (i+1) % res
            eta1 = delta * i
            eta2 = delta * j

            co1, dco1 = path_point(eta1)
            co2, dco2 = path_point(eta2)

            t = tan((eta2 - eta1) * 0.5)
            alpha = sin(eta2 - eta1) * (sqrt(4.0 + 3.0*t*t) - 1.0) / 3.0

            handle1_right = co1 + alpha * dco1
            handle2_left = co2 - alpha * dco2

            yield co1, co2, handle1_right, handle2_left
    
    def write_preset_py(self, file_preset):
        props = ["semimajor",
                 "eccentricity",
                 "inclination",
                 "ascending_node",
                 "periapsis_argument",
                 "use_orbital_plane",
                 "mean_anomaly_epoch",
                 "mean_motion",
                 ]
        for p in props:
            file_preset.write("elliptic.{prop} = {value}\n".format(prop=p, value=getattr(self, p)))

    def draw(self, context, layout):
        layout.prop(self, "semimajor")
        layout.prop(self, "eccentricity", slider=True)

        layout.separator()

        layout.prop(self, "use_orbital_plane")
        col = layout.column(align=True)
        col.enabled = self.use_orbital_plane
        col.prop(self, "inclination", slider=True)
        col.prop(self, "ascending_node", slider=True)
        col.prop(self, "periapsis_argument", slider=True)

        layout.separator()

        col = layout.column(align=True)
        col.prop(self, "mean_motion")


_loaded_datafiles = {}

class DistantWorldsData:
    def __init__(self, header, data):
        self.header = header
        self.data = data

def get_datafile(name):
    global _loaded_datafiles

    path = bpy.path.abspath(name)
    return _loaded_datafiles.get(path, None)

def load_datafile(name):
    global _loaded_datafiles

    path = bpy.path.abspath(name)
    if path in _loaded_datafiles:
        raise Exception("Data file '%s' already loaded")

    header = ""
    data = []
    with open(path, mode='r') as df:
        part = 0
        for line in df:
            if part == 0:
                if line.startswith("$$SOE"):
                    part = 1
                    continue
                header += line
            elif part == 1:
                if line.startswith("$$EOE"):
                    part = 2
                    continue
                data.append(line)
            else:
                break

    df = DistantWorldsData(header, data)
    _loaded_datafiles[path] = df
    return df

def unload_datafile(name):
    global _loaded_datafiles

    path = bpy.path.abspath(name)
    if path in _loaded_datafiles:
        del _loaded_datafiles[name]

# Loads orbital ephemerides from a data file
class DistantWorldsDataOrbit(PropertyGroup):
    @property
    def dw(self):
        return self.id_data.distant_worlds

    def clear_data(self):
        unload_datafile(self.filepath)

    def reload_data(self):
        df = get_datafile(self.datafile)
        if df:
            unload_datafile(self.filepath)
            return load_datafile(self.filepath)
        else:
            return None

    def get_data(self):
        df = get_datafile(self.datafile)
        if not df:
            df = load_datafile(self.filepath)
        return df

    # ---------------------------------

    def param_update(self, context):
        body = getattr(context, "distant_worlds_body", None)
        if body:
            body.param_update(context)

    def filepath_update(self, context):
        self.reload_data()
        param_update(context)

    filepath = StringProperty(name="File Path",
                              description="Data file containing ephemerides for the body",
                              subtype='FILE_PATH',
                              update=filepath_update
                              )

    @property
    def matrix_orbit_refplane(self):
        return Matrix.Identity(4)

    def location(self, time):
        return Vector((0,0,0)) # TODO

    def path_segments(self, res):
        return [] # TODO

    def write_preset_py(self, file_preset):
        props = ["filepath",
                 ]
        for p in props:
            file_preset.write("datafile.{prop} = {value}\n".format(prop=p, value=getattr(self, p)))

    def draw(self, context, layout):
        layout.prop(self, "filepath")


# Orbital parameters and settings
class DistantWorldsOrbitParams(PropertyGroup):
    @property
    def dw(self):
        return self.id_data.distant_worlds

    def param_update(self, context):
        body = getattr(context, "distant_worlds_body", None)
        if body:
            body.param_update(context)

#    elliptic = PointerProperty(name="Elliptic",
#                               description="Elliptic orbit parameters",
#                               type=DistantWorldsEllipticalOrbit)
#    datafile = PointerProperty(name="Data File Settings",
#                               description="Settings for ephemerides from file data",
#                               type=DistantWorldsDataOrbit)

    # Options
    use_scene_time = BoolProperty(name="Use Scene Time",
                                  description="Move the body during animation",
                                  default=True,
                                  update=param_update
                                  )

    orbit_type_items = [
        ("ELLIPTIC", "Elliptic", "Regular elliptical orbit", 'NONE', 0),
        #("HYPERBOLIC", "Hyperbolic", "Aperiodic path", 'NONE', 1),
        ("DATA", "Data", "Use external data for path", 'NONE', 2),
    ]

    type = EnumProperty(name="Type",
                        items=orbit_type_items,
                        update=param_update,
                        )

    @property
    def scale(self):
        return self.dw.scene_scale

    def location(self, time):
        if self.type == 'ELLIPTIC':
            return self.elliptic.location(time)
        elif self.type == 'DATA':
            return self.datafile.location(time)

    def path_segments(self, res):
        if self.type == 'ELLIPTIC':
            return self.elliptic.path_segments(res)
        elif self.type == 'DATA':
            return self.datafile.path_segments(res)

    def path_is_periodic(self):
        return self.type in {'ELLIPTIC'}

    @property
    def matrix_orbit_refplane(self):
        if self.type == 'ELLIPTIC':
            return self.elliptic.matrix_orbit_refplane
        elif self.type == 'DATA':
            return self.datafile.matrix_orbit_refplane

    # TODO
    @property
    def matrix_equator_orbit(self):
        """Transformation from the body's equator plane to the orbital plane"""
        return Matrix.Identity(4)

    @property
    def matrix_equator_refplane(self):
        return self.matrix_orbit_refplane * self.matrix_equator_orbit

    @property
    def current_time(self):
        if self.use_scene_time:
            return self.dw.current_sim_time
        else:
            # TODO use custom time
            return 0.0

    #### Serialization ####
    
    def write_preset_py(self, file_preset):
        props = ["use_scene_time",
                 ]
        for p in props:
            file_preset.write("orbit.{prop} = {value}\n".format(prop=p, value=getattr(self, p)))

        file_preset.write("elliptic = orbit.elliptic\n")
        self.elliptic.write_preset_py(file_preset)

        file_preset.write("datafile = orbit.datafile\n")
        self.datafile.write_preset_py(file_preset)

    def draw(self, context, layout):
        layout.prop(self, "type", text="Orbit Type")
        if self.type == 'ELLIPTIC':
            self.elliptic.draw(context, layout)
        elif self.type == 'DATA':
            self.datafile.draw(context, layout)


def register():
    bpy.utils.register_class(DistantWorldsEllipticalOrbit)
    bpy.utils.register_class(DistantWorldsDataOrbit)
    
    DistantWorldsOrbitParams.elliptic = \
        PointerProperty(name="Elliptic",
                        description="Elliptic orbit parameters",
                        type=DistantWorldsEllipticalOrbit)
    DistantWorldsOrbitParams.datafile = \
        PointerProperty(name="Data File Settings",
                        description="Settings for ephemerides from file data",
                        type=DistantWorldsDataOrbit)
    bpy.utils.register_class(DistantWorldsOrbitParams)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOrbitParams)
    bpy.utils.unregister_class(DistantWorldsEllipticalOrbit)

if __name__ == "__main__":
    register()
