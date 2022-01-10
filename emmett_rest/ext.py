# -*- coding: utf-8 -*-
"""
    emmett_rest.ext
    ---------------

    Provides REST extension for Emmett

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from emmett.extensions import Extension, Signals, listen_signal
from emmett.orm.models import MetaModel

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
        default_sort='id',
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
