# -*- coding: utf-8 -*-
"""
    emmett_rest.parsers
    -------------------

    Provides REST de-serialization tools

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from collections import OrderedDict
from typing import List, Optional

from emmett import request, sdict
from emmett.utils import cachedprop


class VParserDefinition:
    __slots__ = ['param', 'f']

    def __init__(self, param):
        self.param = param

    def __call__(self, f):
        self.f = f
        return self


class ProcParserDefinition:
    __slots__ = ['f', '_inst_count_']
    _all_inst_count_ = 0

    def __init__(self):
        self._inst_count_ = self.__class__._all_inst_count_
        self.__class__._all_inst_count_ += 1

    def __call__(self, f):
        self.f = f
        return self


class MetaParser(type):
    def __new__(cls, name, bases, attrs):
        new_class = type.__new__(cls, name, bases, attrs)
        all_vparsers = {}
        all_procs = OrderedDict()
        declared_vparsers = {}
        declared_procs = OrderedDict()
        procs = []
        for key, value in list(attrs.items()):
            if isinstance(value, VParserDefinition):
                declared_vparsers[key] = value
            elif isinstance(value, ProcParserDefinition):
                procs.append((key, value))
        procs.sort(key=lambda x: x[1]._inst_count_)
        declared_procs.update(procs)
        new_class._declared_vparsers_ = declared_vparsers
        new_class._declared_procs_ = declared_procs
        for base in reversed(new_class.__mro__[1:]):
            if hasattr(base, '_declared_vparsers_'):
                all_vparsers.update(base._declared_vparsers_)
            if hasattr(base, '_declared_procs_'):
                all_procs.update(base._declared_procs_)
        all_vparsers.update(declared_vparsers)
        all_procs.update(declared_procs)
        new_class._all_vparsers_ = all_vparsers
        new_class._all_procs_ = all_procs
        vparams = []
        vparsers = {}
        for vparser in all_vparsers.values():
            vparsers[vparser.param] = vparser.f
            vparams.append(vparser.param)
        new_class._vparsers_ = vparsers
        new_class._vparams_ = set(vparams)
        return new_class

    @classmethod
    def parse_value(cls, param):
        return VParserDefinition(param)

    @classmethod
    def processor(cls):
        return ProcParserDefinition()


class Parser(metaclass=MetaParser):
    attributes: List[str] = []
    include: List[str] = []
    exclude: List[str] = []
    envelope: Optional[str] = None

    def __init__(self, model):
        self._model = model
        if not self.attributes:
            self.attributes = []
            writable_map = {}
            for fieldname in self._model.table.fields:
                writable_map[fieldname] = self._model.table[fieldname].writable
            if hasattr(self._model, 'rest_rw'):
                self.attributes = []
                for key, value in self._model.rest_rw.items():
                    if isinstance(value, tuple):
                        writable = value[1]
                    else:
                        writable = value
                    writable_map[key] = writable
            for fieldname, writable in writable_map.items():
                if writable:
                    self.attributes.append(fieldname)
            self.attributes += self.include
            for el in self.exclude:
                if el in self.attributes:
                    self.attributes.remove(el)
        _attrs_override_ = []
        for key in (
            set(dir(self)) - set(self._all_vparsers_.keys()) -
            set(self._all_procs_.keys())
        ):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_
        self._init()

    def _init(self):
        pass

    async def __call__(self, **kwargs):
        return self.__parse_params__(await request.body_params, **kwargs)

    @cachedprop
    def _attributes_set(self):
        return set(self.attributes)

    def __parse_params__(self, body_params, **extras):
        params = _envelope_filter(body_params, self.envelope)
        rv = _parse(self._attributes_set, params)
        for name in set(params) & self._vparams_:
            rv[name] = self._vparsers_[name](self, params[name])
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(params, **extras)
        for processor in self._all_procs_.values():
            processor.f(self, params, rv)
        return rv


def _envelope_filter(params, envelope=None):
    if not envelope:
        return params
    return params[envelope]


def _parse(accepted_set, params):
    rv = sdict()
    for key in accepted_set & set(params):
        rv[key] = params[key]
    return rv


def parse_params_with_parser(parser_instance, **extras):
    return parser_instance(**extras)


async def parse_params(*accepted_params, **kwargs):
    params = _envelope_filter(
        await request.body_params, kwargs.get('envelope')
    )
    return _parse(set(accepted_params), params)
