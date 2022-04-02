# -*- coding: utf-8 -*-
"""
    emmett_rest.ext
    ---------------

    Provides REST extension for Emmett

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import Any, Dict, List, Optional, Type, Union

from emmett.extensions import Extension, Signals, listen_signal
from emmett.orm.models import MetaModel

from .openapi.mod import OpenAPIModule
from .rest import AppModule, RESTModule
from .parsers import Parser
from .serializers import Serializer
from .wrappers import (
    wrap_method_on_obj,
    wrap_module_from_app,
    wrap_module_from_module
)


class REST(Extension):
    default_config = dict(
        default_module_class=RESTModule,
        default_serializer=Serializer,
        default_parser=Parser,
        page_param='page',
        pagesize_param='page_size',
        sort_param='sort_by',
        query_param='where',
        min_pagesize=1,
        max_pagesize=50,
        default_pagesize=20,
        default_sort=None,
        base_path='/',
        id_path='/<int:rid>',
        list_envelope='data',
        single_envelope=False,
        groups_envelope='data',
        use_envelope_on_parse=False,
        serialize_meta=True,
        meta_envelope='meta',
        default_enabled_methods=[
            'index', 'create', 'read', 'update', 'delete'
        ],
        default_disabled_methods=[],
        use_save=True,
        use_destroy=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .serializers import serialize
        from .parsers import parse_params
        self._serialize = serialize
        self._parse_params = parse_params

    @listen_signal(Signals.before_database)
    def _configure_models_attr(self):
        MetaModel._inheritable_dict_attrs_.append(
            ('rest_rw', {'id': (True, False)})
        )

    def on_load(self):
        setattr(AppModule, 'rest_module', wrap_module_from_module(self))
        self.app.rest_module = wrap_method_on_obj(
            wrap_module_from_app(self),
            self.app
        )

    @property
    def module(self):
        return self.config.default_module_class

    @property
    def serialize(self):
        return self._serialize

    @property
    def parse_params(self):
        return self._parse_params

    def docs_module(
        self,
        import_name: str,
        name: str,
        title: str,
        version: str,
        modules_tree_prefix: str,
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        terms_of_service: Optional[str] = None,
        contact: Optional[Dict[str, Union[str, Any]]] = None,
        license_info: Optional[Dict[str, Union[str, Any]]] = None,
        security_schemes: Optional[Dict[str, Any]] = None,
        produce_schemas: bool = False,
        expose_ui: Optional[bool] = None,
        ui_path: str = "/docs",
        url_prefix: Optional[str] = None,
        hostname: Optional[str] = None,
        module_class: Optional[Type[OpenAPIModule]] = None,
        **kwargs: Any
    ):
        module_class = module_class or OpenAPIModule
        return module_class.from_app(
            self.app,
            import_name=import_name,
            name=name,
            template_folder=None,
            template_path=None,
            static_folder=None,
            static_path=None,
            url_prefix=url_prefix,
            hostname=hostname,
            cache=None,
            root_path=None,
            pipeline=[],
            injectors=[],
            opts={
                'title': title,
                'version': version,
                'modules_tree_prefix': modules_tree_prefix,
                'description': description,
                'tags': tags,
                'servers': servers,
                'terms_of_service': terms_of_service,
                'contact': contact,
                'license_info': license_info,
                'security_schemes': security_schemes,
                'produce_schemas': produce_schemas,
                'expose_ui': expose_ui,
                'ui_path': ui_path
            },
            **kwargs
        )
