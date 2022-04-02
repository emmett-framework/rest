# -*- coding: utf-8 -*-
"""
    emmett_rest.openapi.helpers
    ---------------------------

    Provides OpenAPI internal helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from enum import Enum

from emmett import Pipe, response
from yaml import add_multi_representer, dump


class YAMLPipe(Pipe):
    output = "str"

    async def pipe_request(self, next_pipe, **kwargs):
        response.content_type = "text/yaml; charset=utf-8"
        return dump(await next_pipe(**kwargs), sort_keys=False)


add_multi_representer(Enum, lambda d, v: d.represent_data(v.value))
