# -*- coding: utf-8 -*-
"""
    emmett_rest.helpers
    -------------------

    Provides helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

from emmett import request, response
from emmett.pipeline import Pipe
from emmett.routing.router import RoutingCtx

if TYPE_CHECKING:
    from .rest import RESTModule

T = TypeVar("T")


class RESTRoutingCtx:
    def __init__(self, module: RESTModule, ctx: RoutingCtx):
        self._rest_module = module
        self._wrapped_ctx = ctx

    def __call__(self, f: T) -> T:
        openapi_include = getattr(f, "_openapi_spec", False)
        rv = self._wrapped_ctx(f)
        if openapi_include:
            self._rest_module._openapi_specs["additional_routes"].append(
                (self._wrapped_ctx.rule.name, f, self._wrapped_ctx.rule)
            )
        return rv


class ModulePipe(Pipe):
    def __init__(self, mod):
        self.mod = mod


class SetFetcher(ModulePipe):
    async def pipe_request(self, next_pipe, **kwargs):
        kwargs['dbset'] = self.mod._fetcher_method()
        return await next_pipe(**kwargs)


class RecordFetcher(ModulePipe):
    async def pipe_request(self, next_pipe, **kwargs):
        self.fetch_record(kwargs)
        if not kwargs['row']:
            response.status = 404
            return self.mod.error_404()
        return await next_pipe(**kwargs)

    def fetch_record(self, kwargs):
        kwargs['row'] = self.mod._select_method(
            kwargs['dbset'].where(self.mod.model.id == kwargs['rid']))
        del kwargs['rid']
        del kwargs['dbset']


class FieldPipe(ModulePipe):
    def __init__(self, mod, accepted_attr_name, arg='field'):
        super().__init__(mod)
        self.accepted_attr_name = accepted_attr_name
        self.arg_name = arg
        self.set_accepted()

    def set_accepted(self):
        self._accepted_dict = {
            val: self.mod.model.table[val]
            for val in getattr(self.mod, self.accepted_attr_name)
        }

    async def pipe_request(self, next_pipe, **kwargs):
        field = self._accepted_dict.get(kwargs[self.arg_name])
        if not field:
            response.status = 404
            return self.mod.build_error_404()
        kwargs[self.arg_name] = field
        return await next_pipe(**kwargs)


class FieldsPipe(ModulePipe):
    def __init__(
        self,
        mod,
        accepted_attr_name,
        query_param_name='fields',
        arg='fields'
    ):
        super().__init__(mod)
        self.accepted_attr_name = accepted_attr_name
        self.param_name = query_param_name
        self.arg_name = arg
        self.set_accepted()

    def set_accepted(self):
        self._accepted_set = set(getattr(self.mod, self.accepted_attr_name))

    def parse_fields(self):
        pfields = (
            (
                isinstance(request.query_params[self.param_name], str) and
                request.query_params[self.param_name]
            ) or ''
        ).split(',')
        sfields = self._accepted_set & set(pfields)
        return [self.mod.model.table[key] for key in sfields]

    async def pipe_request(self, next_pipe, **kwargs):
        fields = self.parse_fields()
        if not fields:
            response.status = 400
            return self.mod.build_error_400({
                self.param_name: 'invalid value'
            })
        kwargs[self.arg_name] = fields
        return await next_pipe(**kwargs)
