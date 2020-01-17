# -*- coding: utf-8 -*-
"""
    emmett_rest.wrappers
    --------------------

    Provides wrappers for the REST extension

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from functools import wraps
from typing import Callable, Generic, List, Optional

from .helpers import DEFAULT


def wrap_module_from_app(ext: Generic) -> Callable[..., Generic]:
    def rest_module_from_app(
        app: Generic,
        import_name: str,
        name: str,
        model: Generic,
        serializer: Optional[Generic] = None,
        parser: Optional[Generic] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[str] = DEFAULT,
        meta_envelope: Optional[str] = DEFAULT,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Generic] = None
    ) -> Generic:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_app(
            ext, import_name, name, model, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope, meta_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname
        )
    return rest_module_from_app


def wrap_module_from_module(ext: Generic) -> Callable[..., Generic]:
    def rest_module_from_module(
        mod: Generic,
        import_name: str,
        name: str,
        model: Generic,
        serializer: Optional[Generic] = None,
        parser: Optional[Generic] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
        list_envelope: Optional[str] = None,
        single_envelope: Optional[str] = DEFAULT,
        meta_envelope: Optional[str] = DEFAULT,
        use_envelope_on_parse: Optional[bool] = None,
        serialize_meta: Optional[bool] = None,
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Generic] = None
    ) -> Generic:
        module_class = module_class or ext.config.default_module_class
        return module_class.from_module(
            ext, mod, import_name, name, model, serializer, parser,
            enabled_methods, disabled_methods,
            list_envelope, single_envelope, meta_envelope,
            use_envelope_on_parse, serialize_meta,
            url_prefix, hostname
        )
    return rest_module_from_module


def wrap_method_on_obj(method, obj):
    @wraps(method)
    def wrapped(*args, **kwargs):
        return method(obj, *args, **kwargs)
    return wrapped
