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

import bpy, hashlib
from bpy.types import PropertyGroup, BlendData, ID, UILayout
from bpy_types import RNAMetaPropGroup
from bpy.props import *

_idtypes = dict()
for key, c in BlendData.bl_rna.properties.items():
    if c.type == 'COLLECTION' and isinstance(c.fixed_type, ID):
        _idtypes[c.fixed_type.bl_rna.identifier] = (c.fixed_type, key)

_idtype_items = [
    (
        t.bl_rna.identifier,
        t.bl_rna.name,
        t.bl_rna.description,
        UILayout.icon(t.bl_rna),
        hash(t.bl_rna.identifier),
    )
    for t, _ in _idtypes.values()]

'''
class IDReference(PropertyGroup):
    idtype = EnumProperty(name="Type", description="Type of the ID datablock", items=_idtype_items)
    idname = StringProperty(name="ID datablock name", description="Name of the datablock")
    idlib = StringProperty(name="Library path", description="File path of the ID library")
'''

def IDRefProperty(name, description, type, update=None):
    return (IDRefProperty, {
        'name' : name,
        'description' : description,
        'type' : type,
        'update' : update,
        })

def _find_id(rna_type, data_prop, name, lib):
    if not (rna_type and data_prop):
        return None
    data = getattr(bpy.context.blend_data, data_prop, [])
    for ptr in data:
        if ptr.name != name:
            continue
        if ptr.library:
            if lib and ptr.library.filepath == lib:
                return ptr
        else:
            if not lib:
                return ptr
    return None

def make_id_ref_property(attr, **kw):
    idtype = kw['type']
    rna_type, data_prop = _idtypes[idtype]

    def fget(self):
        props = self.get(attr, None)
        if not props:
            return None
        idname = props.get('idname', "")
        idlib = props.get('idlib', "")
        return _find_id(rna_type, data_prop, idname, idlib)

    def fset(self, value):
        props = self.get(attr, None)
        if not props:
            self[attr] = {}
            props = self[attr]
        if value is None:
            props['idname'] = ""
            props['idlib'] = ""
        else:
            if isinstance(value, rna_type):
                props['idname'] = value.name
                props['idlib'] = value.library.filepath if value.library else ""
            else:
                raise ValueError("Invalid ID type %s, expected %s" % (value.bl_rna.identifier, rna_type.bl_rna.identifier))

    def fdel(self):
        if attr in self:
            del self[attr]

    return property(fget=fget, fset=fset, fdel=fdel, doc=kw.get('description', None))

def make_id_ref_enum(attr, **kw):
    idtype = kw['type']
    rna_type, data_prop = _idtypes[idtype]

    def enum_uid(name, lib):
        m = hashlib.md5()
        m.update(name.encode())
        m.update(lib.encode())
        uid = m.hexdigest()
        return uid, hash(uid) & 0xffff

    uid_none, index_none = enum_uid("", "")

    def id_items(self, context):
        desc = rna_type.bl_rna.description
        icon = UILayout.icon(rna_type.bl_rna)

        items = [(uid_none, "", "", 0, index_none)]
        data = getattr(context.blend_data, data_prop, [])
        for ptr in data:
            name = ptr.name
            lib = ptr.library.filepath if ptr.library else ""
            uid, index = enum_uid(name, lib)
            items.append((uid, name, desc, icon, index))
        return items

    def id_get(self):
        props = self.get(attr, None)
        if not props:
            return index_none
        idname = props.get('idname', "")
        idlib = props.get('idlib', "")
        uid, index = enum_uid(idname, idlib)
        return index

    def id_set(self, value):
        props = self.get(attr, None)
        if not props:
            self[attr] = {}
            props = self[attr]
        data = getattr(bpy.context.blend_data, data_prop, [])
        for ptr in data:
            name = ptr.name
            lib = ptr.library.filepath if ptr.library else ""
            uid, index = enum_uid(name, lib)
            if index == value:
                props['idname'] = name
                props['idlib'] = lib
                return
        props['idname'] = ""
        props['idlib'] = ""

    return EnumProperty(name=kw['name'], description=kw.get('description', None), items=id_items, get=id_get, set=id_set)

class DistantWorldsPropertyGroup(RNAMetaPropGroup):
    def __new__(cls, name, parents, dct):
        # register IDRef properties
        newdct = dct.copy()
        for key, value in dct.items():
            if isinstance(value, tuple):
                if value[0] == IDRefProperty:
                    newdct[key] = make_id_ref_property(key, **value[1])
                    newdct[key+'__enum'] = make_id_ref_enum(key, **value[1])

        # we need to call type.__new__ to complete the initialization
        return super(DistantWorldsPropertyGroup, cls).__new__(cls, name, parents, newdct)
