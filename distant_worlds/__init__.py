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
    "name": "Distant Worlds",
    "author": "Lukas Toenne",
    "version": (0, 1, 0),
    "blender": (2, 7, 4),
    "location": "Scene Properties",
    "description": "Solar system bodies",
    "warning": "",
    "category": "Community"}

import bpy
from distant_worlds import idmap, objects, orbit, body, scene, settings, ui

# Warning: order of registration can be important
# unregister calls should be strictly reverse
 
def register():
    idmap.register()
    settings.register()
    orbit.register()
    body.register()
    objects.register()
    scene.register()
    ui.register()

def unregister():
    ui.unregister()
    scene.unregister()
    objects.unregister()
    body.unregister()
    orbit.unregister()
    settings.unregister()
    idmap.unregister()

if __name__ == "__main__":
    register()
