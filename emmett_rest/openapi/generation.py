# -*- coding: utf-8 -*-
"""
    emmett_rest.openapi.generation
    ------------------------------

    Provides OpenAPI generation functions

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

import datetime
import decimal
import re

from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union, get_type_hints

from pydantic import BaseModel, Field, create_model
from pydantic.config import BaseConfig
from pydantic.fields import FieldInfo, ModelField
from pydantic.schema import field_schema, model_process_schema

from ..rest import RESTModule
from ..serializers import Serializer
from ..parsers import Parser
from .schemas import OpenAPI

REF_PREFIX = "#/components/schemas/"

_re_path_param = re.compile(r"<(\w+)\:(\w+)>")
_re_path_param_optional = re.compile(r"\(([^<]+)?<(\w+)\:(\w+)>\)\?")
_pydantic_baseconf = BaseConfig()
_path_param_types_map = {
    "alpha": str,
    "any": str,
    "date": str,
    "float": float,
    "int": int,
    "str": str
}
_model_field_types_map = {
    "id": int,
    "string": str,
    "text": str,
    "blob": str,
    "bool": bool,
    "int": int,
    "float": float,
    "decimal": decimal.Decimal,
    "date": datetime.date,
    "datetime": datetime.datetime,
    "time": datetime.time,
    "json": Dict[str, Any],
    "jsonb": Dict[str, Any],
    "geography": str,
    "geometry": str,
    "password": str,
    "upload": str,
    "list:string": List[str],
    "list:int": List[int]
}
_def_summaries = {
    "index": "List {entity}",
    "read": "Retrieve {entity}",
    "create": "Create {entity}",
    "update": "Update {entity}",
    "delete": "Delete {entity}"
}


class IndexMetaModel(BaseModel):
    object: str = "list"
    has_more: bool = False
    total_objects: int = 0


class ErrorsModel(BaseModel):
    errors: Dict[str, Any] = Field(default_factory=dict)


def _defs_from_item(obj: Any, key: str):
    rv = defaultdict(list)
    try:
        if issubclass(obj, BaseModel):
            rv[obj].append(key)
            rv.update(_defs_from_pydantic_model(obj, parent=key))
        elif issubclass(obj, Enum):
            rv[obj].append(key)
    except:
        pass
    return rv


def _defs_from_pydantic_model(obj: Type[BaseModel], parent: Optional[str] = None):
    rv = defaultdict(list)
    for key, field in obj.__fields__.items():
        parent_key = f"{parent}.{key}" if parent else key
        for ikey, ival in _defs_from_item(field.type_, parent_key).items():
            rv[ikey].extend(ival)
    return rv


def _denormalize_schema(schema: Dict[str, Any], defs: Dict[str, Dict[str, Any]]):
    obj_type = schema.get("type")
    if "$ref" in schema:
        schema.update(defs[schema.pop("$ref")[14:]])
    elif obj_type == "object":
        for key, value in list(schema.get("properties", {}).items()):
            if "$ref" in value:
                schema["properties"][key] = defs[value["$ref"][14:]]
    elif obj_type == "array":
        if "$ref" in schema.get("items", {}):
            schema["items"] = defs[schema["items"]["$ref"][14:]]
    elif "anyOf" in schema:
        for idx, element in list(enumerate(schema["anyOf"])):
            if "$ref" in element:
                schema["anyOf"][idx] = defs[element["$ref"][14:]]


def _index_default_query_parameters(module: RESTModule) -> List[Dict[str, Any]]:
    rv = []

    model_map = {}
    enums = {module.ext.config.sort_param: []}
    for field in module.allowed_sorts:
        enums[module.ext.config.sort_param].extend([field, f"-{field}"])

    condition_fields = {key: (Any, None) for key in module.query_allowed_fields}

    fields = [
        ModelField(
            name=module.ext.config.page_param,
            type_=int,
            class_validators=None,
            model_config=_pydantic_baseconf,
            required=False,
            default=1,
            field_info=FieldInfo(ge=1)
        ),
        ModelField(
            name=module.ext.config.pagesize_param,
            type_=int,
            class_validators=None,
            model_config=_pydantic_baseconf,
            required=False,
            default=module.ext.config.default_pagesize,
            field_info=FieldInfo(
                description="Size of the page",
                ge=module.ext.config.min_pagesize,
                le=module.ext.config.max_pagesize
            )
        ),
        ModelField(
            name=module.ext.config.sort_param,
            type_=List[str],
            class_validators=None,
            model_config=_pydantic_baseconf,
            required=False,
            default=module.default_sort,
            field_info=FieldInfo(
                description=(
                    "Sort results using the specified attribute(s). "
                    "Descendant sorting applied with -{parameter} notation. "
                    "Multiple values should be separated by comma."
                )
            )
        )
    ]

    if condition_fields:
        where_model = create_model('Condition', **condition_fields)
        fields.append(
            ModelField(
                name=module.ext.config.query_param,
                type_=where_model,
                class_validators=None,
                model_config=_pydantic_baseconf,
                required=False,
                field_info=FieldInfo(
                    description=(
                        "Filter results using the provided query object."
                    )
                )
            )
        )
        model_map[where_model] = 'Condition'

    for field in fields:
        schema, defs, _ = field_schema(
            field, model_name_map=model_map, ref_prefix=None
        )
        if field.name in enums:
            schema["items"]["enum"] = enums[field.name]
        elif field.name == module.ext.config.query_param:
            schema["allOf"][0] = defs["Condition"]
        rv.append({
            "name": field.name,
            "in": "query",
            "required": field.required,
            "schema": schema
        })
    return rv


def build_schema_from_fields(
    module: RESTModule,
    fields: Dict[str, Any],
    hints_check: Optional[Set[str]] = None
) -> Tuple[Dict[str, Any], Type[BaseModel]]:
    hints_check = hints_check if hints_check is not None else set(fields.keys())
    schema_fields, hints_defs, fields_choices = {}, defaultdict(list), {}
    for key, defdata in fields.items():
        choices = None
        if isinstance(defdata, (list, tuple)):
            if len(defdata) == 3:
                type_hint, type_default, choices = defdata
            else:
                type_hint, type_default = defdata
        else:
            type_hint = defdata
            type_default = ...
        schema_fields[key] = (type_hint, type_default)
        if choices:
            fields_choices[key] = choices
    for key in set(schema_fields.keys()) & hints_check:
        for type_arg in [schema_fields[key][0]] + list(getattr(
            schema_fields[key][0], "__args__", []
        )):
            for ikey, ival in _defs_from_item(type_arg, key).items():
                hints_defs[ikey].extend(ival)
    model = create_model(module.model.__name__, **schema_fields)
    schema, defs, nested = model_process_schema(
        model,
        model_name_map={key: key.__name__ for key in hints_defs.keys()},
        ref_prefix=None
    )
    for def_schema in defs.values():
        _denormalize_schema(def_schema, defs)
    for key, value in schema["properties"].items():
        _denormalize_schema(value, defs)
    for key, choices in fields_choices.items():
        schema["properties"][key]["enum"] = choices
    return schema, model


class OpenAPIGenerator:
    def __init__(
        self,
        title: str,
        version: str,
        openapi_version: str = "3.0.2",
        description: Optional[str] = None,
        modules: List[RESTModule] = [],
        modules_tags: Dict[str, str] = {},
        tags: Optional[List[Dict[str, Any]]] = None,
        servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        terms_of_service: Optional[str] = None,
        contact: Optional[Dict[str, Union[str, Any]]] = None,
        license_info: Optional[Dict[str, Union[str, Any]]] = None,
    ):
        self.openapi_version = openapi_version
        self.info: Dict[str, Any] = {"title": title, "version": version}
        if description:
            self.info["description"] = description
        if terms_of_service:
            self.info["termsOfService"] = terms_of_service
        if contact:
            self.info["contact"] = contact
        if license_info:
            self.info["license"] = license_info
        self.modules = modules
        self.modules_tags = modules_tags
        self.tags = tags or []
        self.servers = servers or []

    def fields_from_model(
        self,
        model: Any,
        model_fields: Dict[str, Any],
        fields: List[str]
    ) -> Dict[str, Tuple[Type, Any, List[Any]]]:
        rv = {}
        for key in fields:
            field = model_fields[key]
            ftype = field._type
            choices = None
            if ftype.startswith("decimal"):
                ftype = "decimal"
            if ftype.startswith("reference"):
                ftype = model._belongs_ref_[key].ftype
            if "in" in field._validation and ftype != "bool":
                if isinstance(field._validation["in"], (list, tuple)):
                    choices = list(field._validation["in"])
            rv[key] = (
                _model_field_types_map.get(ftype, Any),
                Field(default_factory=model_fields[key].default)
                if callable(model_fields[key].default) else model_fields[key].default,
                choices
            )
        return rv


    def build_schema_from_parser(
        self,
        module: RESTModule,
        parser: Parser,
        model_fields: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Type[BaseModel]]:
        model_fields = model_fields or {
            key: module.model.table[key]
            for key in module.model._instance_()._fieldset_all
        }
        fields, hints_check = self.fields_from_model(
            module.model, model_fields, parser.attributes
        ), set()
        for key, defdata in getattr(parser, '_openapi_def_fields', {}).items():
            if isinstance(defdata, (list, tuple)):
                type_hint, type_default = defdata
            else:
                type_hint = defdata
                type_default = ...
            fields[key] = (type_hint, type_default)
            hints_check.add(key)
        return build_schema_from_fields(module, fields, hints_check)


    def build_schema_from_serializer(
        self,
        module: RESTModule,
        serializer: Serializer,
        model_fields: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Type[BaseModel]]:
        model_fields = model_fields or {
            key: module.model.table[key]
            for key in module.model._instance_()._fieldset_all
        }
        fields, hints_check = self.fields_from_model(
            module.model, model_fields, serializer.attributes
        ), set()
        for key in serializer._attrs_override_:
            type_hint = get_type_hints(getattr(serializer, key)).get('return', Any)
            type_hint_opt = False
            for type_arg in getattr(type_hint, "__args__", []):
                if issubclass(type_arg, type(None)):
                    type_hint_opt = True
            fields[key] = (type_hint, None if type_hint_opt else ...)
            hints_check.add(key)
        for key, defdata in getattr(serializer, '_openapi_def_fields', {}).items():
            if isinstance(defdata, (list, tuple)):
                type_hint, type_default = defdata
            else:
                type_hint = defdata
                type_default = ...
            fields[key] = (type_hint, type_default)
            hints_check.add(key)
        return build_schema_from_fields(module, fields, hints_check)


    def build_definitions(self, module: RESTModule) -> Dict[str, Any]:
        serializers, parsers = {}, {}
        model_fields = {
            key: module.model.table[key]
            for key in module.model._instance_()._fieldset_all
        }
        for serializer_name, serializer in {
            "__default__": module.serializer,
            **module._openapi_specs["serializers"]
        }.items():
            if serializer in serializers:
                continue
            data = serializers[serializer] = {}
            serializer_schema, serializer_model = self.build_schema_from_serializer(
                module, serializer, model_fields
            )
            data.update(
                name=serializer_name,
                model=serializer_model,
                schema=serializer_schema
            )

        for parser_name, parser in {
            "__default__": module.parser,
            **module._openapi_specs["parsers"]
        }.items():
            if parser in parsers:
                continue
            data = parsers[parser] = {}
            parser_schema, parser_model = self.build_schema_from_parser(
                module, parser, model_fields
            )
            data.update(
                name=parser_name,
                model=parser_model,
                schema=parser_schema
            )

        return {
            "module": module.name,
            "model": module.model.__name__,
            "serializers": serializers,
            "parsers": parsers,
            "schema": serializers[module.serializer]["schema"]
        }


    def build_operation_metadata(
        self,
        module: RESTModule,
        modules_tags: Dict[str, str],
        route_kind: str,
        method: str
    ) -> Dict[str, Any]:
        # TODO: description, deprecated
        return {
            "summary": _def_summaries[route_kind].format(
                entity=module.name.rsplit(".", 1)[-1]
            ),
            "operationId": f"{module.name}.{route_kind}.{method}".replace(".", "_"),
            # "tags": [module.name]
            "tags": [modules_tags[module.name]]
        }

    def build_operation_parameters(
        self,
        module: RESTModule,
        path_kind: str,
        path_params: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        rv = []
        for pname, pdata in path_params.items():
            rv.append({
                "name": pname,
                "in": "path",
                "required": not pdata["optional"],
                "schema": field_schema(
                    ModelField(
                        name=pname,
                        type_=_path_param_types_map[pdata["type"]],
                        class_validators=None,
                        model_config=_pydantic_baseconf,
                        required=not pdata["optional"]
                    ),
                    model_name_map={},
                    ref_prefix=REF_PREFIX
                )[0]
            })
        if path_kind == "index":
            rv.extend(_index_default_query_parameters(module))
        return rv


    def build_operation_common_responses(
        self,
        module: RESTModule,
        path_kind: str
    ) -> Dict[str, Any]:
        rv = {}
        error_schema = model_process_schema(
            ErrorsModel,
            model_name_map={},
            ref_prefix=None
        )[0]
        if path_kind in ["read", "update", "delete"]:
            rv["404"] = {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": error_schema
                    }
                }
            }
        if path_kind in ["create", "update"]:
            rv["422"] = {
                "description": "Unprocessable request",
                "content": {
                    "application/json": {
                        "schema": error_schema
                    }
                }
            }
        return rv


    def build_index_schema(
        self,
        module: RESTModule,
        item_model: BaseModel,
        item_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        fields = {module.list_envelope: (List[Dict[str, Any]], ...)}
        if module.serialize_meta:
            fields[module.meta_envelope] = (IndexMetaModel, ...)
        schema, defs, nested = model_process_schema(
            create_model(f"{module.__class__.__name__}Index", **fields),
            model_name_map={
                IndexMetaModel: "Meta",
                item_model: item_model.__name__
            },
            ref_prefix=None
        )
        schema["properties"][module.list_envelope]["items"] = item_schema
        if module.serialize_meta:
            schema["properties"][module.meta_envelope] = defs["Meta"]
            schema["properties"][module.meta_envelope]["title"] = "Meta"
        return schema

    def build_paths(
        self,
        module: RESTModule,
        modules_tags: Dict[str, str],
        serializers: Dict[Serializer, Dict[str, Any]],
        parsers: Dict[Parser, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        rv: Dict[str, Dict[str, Dict[str, Any]]] = {}
        mod_name = module.name.rsplit('.', 1)[-1]

        for path_kind in set(module.enabled_methods) & {
            "index",
            "create",
            "read",
            "update",
            "delete"
        }:
            path_relative, methods = module._methods_map[path_kind]
            if not isinstance(methods, list):
                methods = [methods]
            path_scoped: str = module.url_prefix + path_relative
            if path_scoped.endswith("/") and len(path_scoped) > 1:
                path_scoped = path_scoped[:-1]
            path_params = {}
            for ptype, pname in _re_path_param.findall(path_scoped):
                path_params[pname] = {"type": ptype, "optional": False}
                path_scoped = path_scoped.replace(f"<{ptype}:{pname}>", f"{{{pname}}}")
            for _, ptype, pname in _re_path_param_optional.findall(path_scoped):
                path_params[pname]["optional"] = True

            rv[path_scoped] = rv.get(path_scoped) or {}

            serializer_obj = module._openapi_specs["serializers"][path_kind]
            parser_obj = module._openapi_specs["parsers"].get(path_kind, module.parser)

            for method in methods:
                operation = self.build_operation_metadata(
                    module, modules_tags, path_kind, method
                )
                operation_parameters = self.build_operation_parameters(
                    module, path_kind, path_params
                )
                operation_responses = self.build_operation_common_responses(
                    module, path_kind
                )
                if operation_parameters:
                    operation["parameters"] = operation_parameters
                if path_kind in ["create", "update"]:
                    operation["requestBody"] = {
                        "content": {
                            "application/json": {
                                "schema": parsers[parser_obj]["schema"]
                            }
                        }
                    }
                if path_kind in ["create", "read", "update"]:
                    serializer_obj = module._openapi_specs["serializers"][path_kind]
                    response_code = "201" if path_kind == "create" else "200"
                    descriptions = {
                        "create": "Resource created",
                        "read": "Resource",
                        "update": "Resource updated"
                    }
                    operation_responses[response_code] = {
                        "description": descriptions[path_kind],
                        "content": {
                            "application/json": {
                                "schema": serializers[serializer_obj]["schema"]
                            }
                        }
                    }
                elif path_kind == "index":
                    operation_responses["200"] = {
                        "description": "Resource list",
                        "content": {
                            "application/json": {
                                "schema": self.build_index_schema(
                                    module,
                                    serializers[serializer_obj]["model"],
                                    serializers[serializer_obj]["schema"]
                                )
                            }
                        }
                    }
                elif path_kind == "delete":
                    operation_responses["200"] = {
                        "description": "Resource deleted",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {}
                                }
                            }
                        }
                    }
                if operation_responses:
                    operation["responses"] = operation_responses
                rv[path_scoped][method] = operation

        for path_name, path_target, path_data in (
            module._openapi_specs["additional_routes"]
        ):
            methods = path_data.methods
            for path_relative in path_data.paths:
                path_scoped: str = module.url_prefix + path_relative
                if path_scoped.endswith("/") and len(path_scoped) > 1:
                    path_scoped = path_scoped[:-1]
                path_params = {}
                for ptype, pname in _re_path_param.findall(path_scoped):
                    path_params[pname] = {"type": ptype, "optional": False}
                    path_scoped = path_scoped.replace(
                        f"<{ptype}:{pname}>", f"{{{pname}}}"
                    )
                for _, ptype, pname in _re_path_param_optional.findall(path_scoped):
                    path_params[pname]["optional"] = True

                rv[path_scoped] = rv.get(path_scoped) or {}

                for method in methods:
                    operation = {
                        "summary": getattr(
                            path_target,
                            "_openapi_desc",
                            f"{{name}} {path_name.rsplit('.', 1)[-1]}"
                        ).format(name=mod_name),
                        "operationId": f"{path_name}.{method}".replace(".", "_"),
                        "tags": [modules_tags[module.name]]
                    }
                    operation_parameters = self.build_operation_parameters(
                        module, "custom", path_params
                    )
                    operation_responses = {}
                    if operation_parameters:
                        operation["parameters"] = operation_parameters

                    operation_request = getattr(
                        path_target, "_openapi_def_request", None
                    )
                    if operation_request:
                        schema = build_schema_from_fields(
                            module,
                            operation_request["fields"]
                        )[0]
                        for file_param in operation_request["files"]:
                            schema["properties"][file_param] = {
                                "type": "string",
                                "format": "binary"
                            }
                        operation["requestBody"] = {
                            "content": {
                                operation_request["content"]: {
                                    "schema": schema
                                }
                            }
                        }
                    else:
                        parser = getattr(
                            path_target, "_openapi_def_parser", module.parser
                        )
                        if parser in parsers:
                            schema = parsers[parser]["schema"]
                        else:
                            schema = self.build_schema_from_parser(module, parser)[0]
                        operation["requestBody"] = {
                            "content": {
                                "application/json": {
                                    "schema": schema
                                }
                            }
                        }

                    operation_responses = {}
                    operation_response = getattr(
                        path_target, "_openapi_def_response", None
                    )
                    if operation_response:
                        schema = build_schema_from_fields(
                            module,
                            operation_response["fields"]
                        )[0]
                        operation_responses[operation_response["code"]] = {
                            "content": {
                                operation_response["content"]: {
                                    "schema": schema
                                }
                            }
                        }
                    else:
                        serializer = getattr(
                            path_target, "_openapi_def_serializer", module.serializer
                        )
                        if serializer in serializers:
                            schema = serializers[serializer]["schema"]
                        else:
                            schema = self.build_schema_from_serializer(
                                module, serializer
                            )[0]
                        operation_responses["200"] = {
                            "content": {
                                "application/json": {
                                    "schema": schema
                                }
                            }
                        }

                    if operation_responses:
                        operation["responses"] = operation_responses

                    rv[path_scoped][method] = operation

        return rv

    def __call__(self, produce_schemas: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {"openapi": self.openapi_version, "info": self.info}
        components: Dict[str, Dict[str, Any]] = {}
        paths: Dict[str, Dict[str, Any]] = {}
        definitions: Dict[str, Dict[str, Any]] = {}
        if self.servers:
            data["servers"] = self.servers
        for module in self.modules:
            defs = self.build_definitions(module)
            # tags.append({
            #     "name": module.name,
            #     "description": module.name.split(".")[-1].title()
            # })
            paths.update(
                self.build_paths(
                    module,
                    self.modules_tags,
                    defs["serializers"],
                    defs["parsers"]
                )
            )
            definitions[module.name] = defs
        if definitions and produce_schemas:
            components["schemas"] = {
                v["model"]: definitions[k]["schema"]
                for k, v in sorted(definitions.items(), key=lambda i: i[1]["model"])
            }
        if components:
            data["components"] = components
        data["paths"] = paths
        if self.tags:
            data["tags"] = self.tags
        return OpenAPI(**data).dict(by_alias=True, exclude_none=True)


def build_schema(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.0.2",
    description: Optional[str] = None,
    modules: List[RESTModule],
    modules_tags: Dict[str, str],
    produce_schemas: bool = False,
    tags: Optional[List[Dict[str, Any]]] = None,
    servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
    terms_of_service: Optional[str] = None,
    contact: Optional[Dict[str, Union[str, Any]]] = None,
    license_info: Optional[Dict[str, Union[str, Any]]] = None,
    generator_cls: Optional[Type[OpenAPIGenerator]] = None
) -> Dict[str, Any]:
    generator_cls = generator_cls or OpenAPIGenerator
    generator = generator_cls(
        title=title,
        version=version,
        openapi_version=openapi_version,
        description=description,
        modules=modules,
        modules_tags=modules_tags,
        tags=tags,
        servers=servers,
        terms_of_service=terms_of_service,
        contact=contact,
        license_info=license_info
    )
    return generator(produce_schemas=produce_schemas)
