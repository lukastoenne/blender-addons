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

import bpy, re

def get_dw(context):
    return context.scene.distant_worlds if context.scene else None

def increment_name(name):
    m = re.match(r"(.*[.^\d])([0]*)(\d+)", name)
    if m:
        prefix = m.group(1)
        padding = len(m.group(2))
        index = int(m.group(3))
        fmt_str = "{{}}{{:0{}d}}".format(padding)
        return fmt_str.format(prefix, index + 1)
    
    m = re.match(r"([0]*)(\d+)", name)
    if m:
        padding = len(m.group(1))
        index = int(m.group(2))
        fmt_str = "{{:0{}d}}".format(padding)
        return fmt_str.format(index + 1)
    
    return "{}.{:03d}".format(name, 1)

def unique_name(collection, item, get_name=lambda x: x.name, next_name=increment_name):
    name_set = {get_name(x) for x in collection if x != item}
    name = get_name(item)
    while name in name_set:
        name = next_name(name)
    return name
