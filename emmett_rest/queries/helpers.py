# -*- coding: utf-8 -*-
"""
    emmett_rest.queries.helpers
    ---------------------------

    Provides REST query language helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from emmett import request, response
from emmett.parsers import Parsers
from typing import Any, Dict

from ..helpers import ModulePipe
from .errors import QueryError
from .parser import parse_conditions as _parse_conditions

_json_load = Parsers.get_for('json')


class JSONQueryPipe(ModulePipe):
    def __init__(self, mod):
        super().__init__(mod)
        self.query_param = mod.ext.config.query_param
        self.set_accepted()

    def set_accepted(self):
        self._accepted_set = set(self.mod._queryable_fields)

    async def pipe_request(self, next_pipe, **kwargs):
        if request.query_params[self.query_param] and self._accepted_set:
            try:
                input_condition = self._parse_where_param(
                    request.query_params[self.query_param]
                )
            except ValueError:
                response.status = 400
                return self.mod.error_400({self.query_param: 'invalid value'})
            try:
                dbset = _parse_conditions(
                    self.mod.model, kwargs['dbset'],
                    input_condition, self._accepted_set
                )
            except QueryError as exc:
                response.status = 400
                return self.mod.error_400({self.query_param: exc.gen_msg()})
            kwargs['dbset'] = dbset
        return await next_pipe(**kwargs)

    @staticmethod
    def _parse_where_param(param: str) -> Dict[str, Any]:
        if not param:
            return {}
        try:
            param = _json_load(param)
            assert isinstance(param, dict)
        except Exception:
            raise ValueError('Invalid param')
        return param
