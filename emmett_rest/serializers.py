# -*- coding: utf-8 -*-
"""
    emmett_rest.serializers
    -----------------------

    Provides REST serialization tools

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import List, Optional

from emmett.orm.objects import Rows


class Serializer:
    attributes: List[str] = []
    include: List[str] = []
    exclude: List[str] = []
    bind_to: Optional[str] = None

    def __init__(self, model):
        self._model = model
        if not self.attributes:
            self.attributes = []
            readable_map = {}
            for fieldname in self._model.table.fields:
                readable_map[fieldname] = self._model.table[fieldname].readable
            if hasattr(self._model, 'rest_rw'):
                self.attributes = []
                for key, value in self._model.rest_rw.items():
                    if isinstance(value, tuple):
                        readable = value[0]
                    else:
                        readable = value
                    readable_map[key] = readable
            for fieldname, readable in readable_map.items():
                if readable:
                    self.attributes.append(fieldname)
            self.attributes += self.include
            for el in self.exclude:
                if el in self.attributes:
                    self.attributes.remove(el)
        _attrs_override_ = []
        for key in dir(self):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_
        self._init()

    def _init(self):
        pass

    def __call__(self, *args, **kwargs):
        return self.__serialize__(*args, **kwargs)

    def __serialize__(self, row, **extras):
        rv = {}
        if self.bind_to:
            row = row[self.bind_to]
        for key in self.attributes:
            rv[key] = row[key]
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(row, **extras)
        return rv


def serialize(objects, serializer, **extras):
    if objects is None:
        return None
    if not objects:
        return []
    elif not isinstance(objects, (Rows, list, tuple)):
        return serialize([objects], serializer, **extras)[0]
    return [serializer(obj, **extras) for obj in objects]
