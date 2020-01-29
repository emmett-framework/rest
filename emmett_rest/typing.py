# -*- coding: utf-8 -*-
"""
    emmett_rest.typing
    ------------------

    Provides typing helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import Type

from emmett.orm import Model

from .parsers import Parser
from .serializers import Serializer


ModelType = Type[Model]
ParserType = Type[Parser]
SerializerType = Type[Serializer]
