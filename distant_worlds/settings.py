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
from bpy.app.handlers import persistent
from distant_worlds import driver

@persistent
def load_post_handler(dummy):
    bpy.app.driver_namespace['distant_worlds'] = driver.driver_namespace

@persistent
def scene_update_post_handler(scene):
    scene.distant_worlds.sync_active_body()

def register():
    bpy.app.handlers.load_post.append(load_post_handler)
    bpy.app.handlers.scene_update_post.append(scene_update_post_handler)

def unregister():
    bpy.app.handlers.load_post.remove(load_post_handler)
    bpy.app.handlers.scene_update_post.remove(scene_update_post_handler)

if __name__ == "__main__":
    register()
