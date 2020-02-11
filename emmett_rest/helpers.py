# -*- coding: utf-8 -*-
"""
    emmett_rest.helpers
    -------------------

    Provides helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett import response
from emmett.pipeline import Pipe

DEFAULT = lambda: None


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
