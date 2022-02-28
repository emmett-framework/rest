# -*- coding: utf-8 -*-
"""
    emmett_rest.openapi.helpers
    ---------------------------

    Provides OpenAPI internal helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett import Pipe, response
from yaml import add_representer, dump

from .schemas import ParameterInType


class YAMLPipe(Pipe):
    output = "str"

    async def pipe_request(self, next_pipe, **kwargs):
        response.content_type = "text/yaml; charset=utf-8"
        return dump(await next_pipe(**kwargs), sort_keys=False)


add_representer(ParameterInType, lambda d, v: d.represent_str(v.value))
