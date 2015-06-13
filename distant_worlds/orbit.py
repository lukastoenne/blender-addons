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
from distant_worlds.driver import *

@body_driver_function
def get_body_orbit_loc(body):
    return body.orbit_params.get_location() if body else Vector((0,0,0))

# Orbital parameters and settings
class DistantWorldsOrbitParams(PropertyGroup):
    @property
    def dw(self):
        return self.id_data.distant_worlds

    def param_update(self, context):
        context.distant_worlds_body.param_update(context)

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

    # TODO
    # mean anomaly at epoch
    mean_anomaly_epoch = 0.0

    # TODO
    mean_motion = 1.0

    def mean_anomaly(self, time):
        return time * self.mean_motion + self.mean_anomaly_epoch

    def eccentric_anomaly(self, time):
        # TODO requires a Newton-Raphson solver step
        return self.mean_anomaly(time)

    def true_anomaly(self, time):
        E = self.eccentric_anomaly(time)
        e = self.eccentricity
        return 2.0 * atan2(sqrt(1.0 - e) * cos(E * 0.5), sqrt(1.0 + e) * sin(E * 0.5))

    def distance(self, time):
        e = self.eccentricity
        v = self.true_anomaly(time)
        return self.semimajor * (1.0 - e*e) / (1.0 + e * cos(v))

    def get_location(self):
        time = self.dw.current_sim_time
        v = self.true_anomaly(time)
        r = self.distance(time)
        p = Vector(( sin(v), cos(v), 0 )) * r
        return p

    def draw(self, context, layout):
        layout.prop(self, "semimajor")
        layout.prop(self, "eccentricity", slider=True)

def register():
    bpy.utils.register_class(DistantWorldsOrbitParams)

def unregister():
    bpy.utils.unregister_class(DistantWorldsOrbitParams)

if __name__ == "__main__":
    register()
