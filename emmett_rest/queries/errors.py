# -*- coding: utf-8 -*-
"""
    emmett_rest.queries.errors
    --------------------------

    Provides REST query language exception classes

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations


class QueryError(ValueError):
    def __init__(self, **kwargs):
        self.init(**kwargs)
        super().__init__(self.gen_msg())

    def init(self, **kwargs):
        self.op = kwargs['op']
        self.value = kwargs['value']

    def gen_msg(self) -> str:
        return "Invalid {} condition: {!r}".format(self.op, self.value)
