# -*- coding: utf-8 -*-
"""
    emmett_rest.wrappers
    --------------------

    Provides wrappers for the REST extension

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from functools import wraps
from typing import Any, Callable, List, Optional, Type, Union

from emmett import App
from emmett.extensions import Extension

from .rest import AppModule, RESTModule
from .typing import ModelType, ParserType, SerializerType


def wrap_module_from_app(ext: Extension) -> Callable[..., RESTModule]:
    def rest_module_from_app(
        app: App,
        import_name: str,
        name: str,
        model: ModelType,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List[str]] = None,
        disabled_methods: Optional[List[str]] = None,
        default_sort: Optional[str] = None,
        use_save: Optional[bool] = None,
        use_destroy: Optional[bool] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        base_path: Optional[str] = None,
        id_path: Optional[str] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Type[RESTModule]] = None,
        **kwargs: Any
    ) -> RESTModule:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_app(
            ext,
            import_name,
            name,
            model,
            serializer=serializer,
            parser=parser,
            enabled_methods=enabled_methods,
            disabled_methods=disabled_methods,
            default_sort=default_sort,
            use_save=use_save,
            use_destroy=use_destroy,
            list_envelope=list_envelope,
            single_envelope=single_envelope,
            meta_envelope=meta_envelope,
            groups_envelope=groups_envelope,
            use_envelope_on_parse=use_envelope_on_parse,
            serialize_meta=serialize_meta,
            base_path=base_path,
            id_path=id_path,
            url_prefix=url_prefix,
            hostname=hostname,
            opts=kwargs
        )
    return rest_module_from_app


def wrap_module_from_module(ext: Extension) -> Callable[..., RESTModule]:
    def rest_module_from_module(
        mod: AppModule,
        import_name: str,
        name: str,
        model: ModelType,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List[str]] = None,
        disabled_methods: Optional[List[str]] = None,
        default_sort: Optional[str] = None,
        use_save: Optional[bool] = None,
        use_destroy: Optional[bool] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[Union[str, bool]] = None,
        meta_envelope: Optional[str] = None,
        groups_envelope: Optional[str] = None,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        base_path: Optional[str] = None,
        id_path: Optional[str] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Type[RESTModule]] = None,
        **kwargs: Any
    ) -> RESTModule:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_module(
            ext,
            mod,
            import_name,
            name,
            model,
            serializer=serializer,
            parser=parser,
            enabled_methods=enabled_methods,
            disabled_methods=disabled_methods,
            default_sort=default_sort,
            use_save=use_save,
            use_destroy=use_destroy,
            list_envelope=list_envelope,
            single_envelope=single_envelope,
            meta_envelope=meta_envelope,
            groups_envelope=groups_envelope,
            use_envelope_on_parse=use_envelope_on_parse,
            serialize_meta=serialize_meta,
            base_path=base_path,
            id_path=id_path,
            url_prefix=url_prefix,
            hostname=hostname,
            opts=kwargs
        )
    return rest_module_from_module


def wrap_method_on_obj(method, obj):
    @wraps(method)
    def wrapped(*args, **kwargs):
        return method(obj, *args, **kwargs)
    return wrapped
