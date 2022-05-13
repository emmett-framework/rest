# -*- coding: utf-8 -*-
"""
    emmett_rest.openapi.api
    -----------------------

    Provides OpenAPI user-facing helpers

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union
)

from pydantic import BaseModel as Schema

if TYPE_CHECKING:
    from ..parsers import Parser
    from ..serializers import Serializer
    from ..rest import RESTModule

T = TypeVar("T")


class ModuleSpec:
    def __init__(self, module: RESTModule):
        self.mod = module


class ModuleDefine(ModuleSpec):
    def serializer(self, serializer: Serializer, routes: List[str]):
        for route in routes:
            self.mod._openapi_specs["serializers"][route] = serializer

    def parser(self, parser: Parser, routes: List[str]):
        for route in routes:
            self.mod._openapi_specs["parsers"][route] = parser


class ModuleDescribe(ModuleSpec):
    def entity(self, name: str):
        self.mod._openapi_specs["entity_name"] = name


class ModuleOpenAPI:
    def __init__(self, module: RESTModule):
        self.define = ModuleDefine(module)
        self.describe = ModuleDescribe(module)


class OpenAPIDefine:
    def schema(self, obj: Schema) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_def_schema = obj
            return f
        return deco

    def fields(self, **specs: Union[Type, Tuple[Type, Any]]) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_def_fields = {**getattr(f, "_openapi_def_fields", {}), **specs}
            return f
        return deco

    def request(
        self,
        content: Optional[str] = None,
        fields: Dict[str, Union[Type, Tuple[Type, Any]]] = {},
        files: List[str] = []
    ) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_def_request = {
                "content": content or "application/json",
                "fields": fields,
                "files": files
            }
            return f
        return deco

    def response(
        self,
        status_code: int = 200,
        content: Optional[str] = None,
        fields: Dict[str, Union[Type, Tuple[Type, Any]]] = {}
    ) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_def_responses = {
                **getattr(f, "_openapi_def_responses", {}),
                **{
                    str(status_code): {
                        "content": content or "application/json",
                        "fields": fields
                    }
                }
            }
            return f
        return deco

    def response_default_errors(self, *error_codes: int) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_def_response_codes = [str(err) for err in error_codes]
            return f
        return deco

    def parser(self, parser: Parser):
        def deco(f: T) -> T:
            f._openapi_def_parser = parser
            return f
        return deco

    def serializer(self, serializer: Serializer):
        def deco(f: T) -> T:
            f._openapi_def_serializer = serializer
            return f
        return deco


class OpenAPIDescribe:
    def __call__(
        self,
        summary: str,
        description: str = ""
    ) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_desc_summary = summary
            f._openapi_desc_description = description
            return f
        return deco

    def summary(self, description: str) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_desc_summary = description
            return f
        return deco

    def description(self, description: str) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_desc_description = description
            return f
        return deco

    def request(self, description: str) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_desc_request = description
            return f
        return deco

    def response(self, description: str) -> Callable[[T], T]:
        def deco(f: T) -> T:
            f._openapi_desc_response = description
            return f
        return deco


class OpenAPI:
    def __init__(self):
        self.define = OpenAPIDefine()
        self.describe = OpenAPIDescribe()

    def include(self, f: T) -> T:
        f._openapi_spec = True
        return f


openapi = OpenAPI()
