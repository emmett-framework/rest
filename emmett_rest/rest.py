# -*- coding: utf-8 -*-
"""
    emmett_rest.rest
    ----------------

    Provides main REST logics

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

import operator

from functools import reduce
from typing import Any, Callable, Dict, List, Optional, Union

from emmett import AppModule, request, response, sdict
from emmett.extensions import Extension
from emmett.orm.objects import Row, Set as DBSet
from emmett.pipeline import Pipe
from emmett.tools.service import JSONServicePipe

from .openapi.api import ModuleOpenAPI
from .helpers import RecordFetcher, SetFetcher, FieldPipe, FieldsPipe, RESTRoutingCtx
from .parsers import (
    parse_params as _parse_params,
    parse_params_with_parser as _parse_params_wparser
)
from .queries import JSONQueryPipe
from .serializers import serialize as _serialize
from .typing import ModelType, ParserType, SerializerType


class RESTModule(AppModule):
    _all_methods = {
        'index',
        'create',
        'read',
        'update',
        'delete',
        'group',
        'stats',
        'sample'
    }

    @classmethod
    def from_app(
        cls,
        ext: Extension,
        import_name: str,
        name: str,
        model: ModelType,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
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
        opts: Dict[str, Any] = {}
    ) -> RESTModule:
        return cls(
            ext,
            name,
            import_name,
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
            **opts
        )

    @classmethod
    def from_module(
        cls,
        ext: Extension,
        mod: AppModule,
        import_name: str,
        name: str,
        model: ModelType,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
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
        opts: Dict[str, Any] = {}
    ) -> RESTModule:
        if '.' in name:
            raise RuntimeError(
                "Nested app modules' names should not contains dots"
            )
        name = mod.name + '.' + name
        if url_prefix and not url_prefix.startswith('/'):
            url_prefix = '/' + url_prefix
        module_url_prefix = (mod.url_prefix + (url_prefix or '')) \
            if mod.url_prefix else url_prefix
        hostname = hostname or mod.hostname
        return cls(
            ext,
            name,
            import_name,
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
            url_prefix=module_url_prefix,
            hostname=hostname,
            pipeline=mod.pipeline,
            **opts
        )

    def __init__(
        self,
        ext: Extension,
        name: str,
        import_name: str,
        model: ModelType,
        serializer: Optional[SerializerType] = None,
        parser: Optional[ParserType] = None,
        enabled_methods: Optional[List] = None,
        disabled_methods: Optional[List] = None,
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
        pipeline: List[Pipe] = [],
        **kwargs: Any
    ):
        if len(model._instance_()._fieldset_pk) > 1:
            raise RuntimeError("Emmett-REST doesn't support multiple PKs models")
        #: overridable methods
        self._fetcher_method = self._get_dbset
        self._select_method = self._get_row
        self.error_400 = self.build_error_400
        self.error_404 = self.build_error_404
        self.error_422 = self.build_error_422
        self.build_meta = self._build_meta
        #: callbacks
        self._before_create_callbacks = []
        self._before_update_callbacks = []
        self._after_params_callbacks = []
        self._after_create_callbacks = []
        self._after_update_callbacks = []
        self._after_delete_callbacks = []
        #: service pipe injection
        add_service_pipe = True
        super_pipeline = list(pipeline)
        if any(
            isinstance(pipe, JSONServicePipe) for pipe in ext.app.pipeline
        ) or any(
            isinstance(pipe, JSONServicePipe) for pipe in super_pipeline
        ):
            add_service_pipe = False
        if add_service_pipe:
            super_pipeline.insert(0, JSONServicePipe())
        #: initialize
        super().__init__(
            ext.app,
            name,
            import_name,
            url_prefix=url_prefix,
            hostname=hostname,
            pipeline=super_pipeline,
            **kwargs
        )
        self.ext = ext
        self._pagination = sdict()
        for key in (
            'page_param', 'pagesize_param',
            'min_pagesize', 'max_pagesize', 'default_pagesize'
        ):
            self._pagination[key] = self.ext.config[key]
        self._sort_param = self.ext.config.sort_param
        self.default_sort = (
            default_sort or
            self.ext.config.default_sort or
            model.table._id.name
        )
        self._path_base = base_path or self.ext.config.base_path
        self._path_rid = id_path or self.ext.config.id_path
        self._serializer_class = serializer or \
            self.ext.config.default_serializer
        self._parser_class = parser or self.ext.config.default_parser
        self._parsing_params_kwargs = {}
        self.model = model
        self.use_save = (
            use_save if use_save is not None else
            self.ext.config.use_save
        )
        self.use_destroy = (
            use_destroy if use_destroy is not None else
            self.ext.config.use_destroy
        )
        self.serializer = self._serializer_class(self.model)
        self.parser = self._parser_class(self.model)
        self.enabled_methods = list(self._all_methods & set(
            list(
                enabled_methods if enabled_methods is not None else
                self.ext.config.default_enabled_methods
            )
        ))
        self.disabled_methods = list(self._all_methods & set(
            list(
                disabled_methods if disabled_methods is not None else
                self.ext.config.default_disabled_methods
            )
        ))
        self.list_envelope = list_envelope or self.ext.config.list_envelope
        self.single_envelope = (
            single_envelope if single_envelope is not None else
            self.ext.config.single_envelope
        )
        self.meta_envelope = (
            meta_envelope if meta_envelope is not None else
            self.ext.config.meta_envelope
        )
        self.groups_envelope = (
            groups_envelope if groups_envelope is not None else
            self.ext.config.groups_envelope
        )
        self.use_envelope_on_parse = (
            use_envelope_on_parse if use_envelope_on_parse is not None else
            self.ext.config.use_envelope_on_parse
        )
        self.serialize_meta = (
            serialize_meta if serialize_meta is not None else
            self.ext.config.serialize_meta
        )
        self._queryable_fields = []
        self._sortable_fields = []
        self._sortable_dict = {}
        self._groupable_fields = []
        self._statsable_fields = []
        self._json_query_pipe = JSONQueryPipe(self)
        self._group_field_pipe = FieldPipe(self, '_groupable_fields')
        self._stats_field_pipe = FieldsPipe(self, '_statsable_fields')
        self.allowed_sorts = [self.default_sort]
        self._openapi_specs = {
            'serializers': {
                key: self.serializer for key in [
                    'index',
                    'create',
                    'read',
                    'update',
                    'delete',
                    'sample'
                ]
            },
            'parsers': {
                key: self.parser for key in [
                    'create',
                    'update'
                ]
            },
            'additional_routes': []
        }
        self.openapi = ModuleOpenAPI(self)
        self._init_pipelines()
        #: custom init
        self.init()
        #: configure module
        self._after_initialize()

    def _init_pipelines(self):
        self.index_pipeline = [SetFetcher(self), self._json_query_pipe]
        self.create_pipeline = []
        self.read_pipeline = [SetFetcher(self), RecordFetcher(self)]
        self.update_pipeline = [SetFetcher(self)]
        self.delete_pipeline = [SetFetcher(self)]
        self.group_pipeline = [
            self._group_field_pipe,
            SetFetcher(self),
            self._json_query_pipe
        ]
        self.stats_pipeline = [
            self._stats_field_pipe,
            SetFetcher(self),
            self._json_query_pipe
        ]
        self.sample_pipeline = [SetFetcher(self), self._json_query_pipe]

    def init(self):
        pass

    def _after_initialize(self):
        self.list_envelope = self.list_envelope or 'data'
        #: adjust single row serialization based on envelope
        self.serialize_many = (
            self.serialize_with_list_envelope_and_meta if self.serialize_meta
            else self.serialize_with_list_envelope
        )
        if self.single_envelope:
            self.serialize_one = self.serialize_with_single_envelope
            if self.use_envelope_on_parse:
                self.parser.envelope = self.single_envelope
                self._parsing_params_kwargs = {'envelope': self.single_envelope}
        else:
            self.serialize_one = self.serialize
        self.pack_data = (
            self.pack_with_list_envelope_and_meta if self.serialize_meta
            else self.pack_with_list_envelope
        )
        #: adjust enabled methods
        for method_name in self.disabled_methods:
            self.enabled_methods.remove(method_name)
        #: route enabled methods
        self._expose_routes()

    def route(
        self,
        paths: Optional[Union[str, List[str]]] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> RESTRoutingCtx:
        rv = super().route(paths, name, **kwargs)
        return RESTRoutingCtx(self, rv)

    def _expose_routes(self):
        path_base_trail = (
            self._path_base.endswith('/') and self._path_base or
            f'{self._path_base}/'
        )
        self._methods_map = {
            'index': (self._path_base, 'get'),
            'read': (self._path_rid, 'get'),
            'create': (self._path_base, 'post'),
            'update': (self._path_rid, ['put', 'patch']),
            'delete': (self._path_rid, 'delete'),
            'group': (f'{path_base_trail}group/<str:field>', 'get'),
            'stats': (f'{path_base_trail}stats', 'get'),
            'sample': (f'{path_base_trail}sample', 'get')
        }
        self._functions_map = {
            **{
                key: f'_{key}'
                for key in self._all_methods - {'create', 'update', 'delete'}
            },
            **{
                key: f'_{key}_without_save' if not self.use_save else f'_{key}'
                for key in {'create', 'update'}
            },
            **{
                key: f'_{key}_without_destroy' if not self.use_destroy else f'_{key}'
                for key in {'delete'}
            }
        }
        for key in self.enabled_methods:
            path, methods = self._methods_map[key]
            pipeline = getattr(self, key + "_pipeline")
            f = getattr(self, self._functions_map[key])
            self.route(path, pipeline=pipeline, methods=methods, name=key)(f)

    def _get_dbset(self) -> DBSet:
        return self.model.all()

    def _get_row(self, dbset: DBSet) -> Optional[Row]:
        return dbset.select(limitby=(0, 1)).first()

    def get_pagination(self):
        try:
            page = int(request.query_params[self._pagination.page_param] or 1)
            assert page > 0
        except Exception:
            page = 1
        try:
            page_size = int(
                request.query_params[self._pagination.pagesize_param] or 20)
            assert (
                self._pagination.min_pagesize <= page_size <=
                self._pagination.max_pagesize)
        except Exception:
            page_size = self._pagination.default_pagesize
        return page, page_size

    def get_sort(self, default=None, allowed_fields=None):
        default = default or self.default_sort
        pfields = (
            (
                isinstance(request.query_params.sort_by, str) and
                request.query_params.sort_by
            ) or default
        ).split(',')
        rv = []
        allowed_fields = allowed_fields or self._sortable_dict
        for pfield in pfields:
            asc = True
            if pfield.startswith('-'):
                pfield = pfield[1:]
                asc = False
            field = allowed_fields.get(pfield)
            if not field:
                continue
            rv.append(field if asc else ~field)
        return reduce(
            lambda a, b: operator.or_(a, b) if a and b else None,
            rv
        ) if rv else allowed_fields.get(default)

    def build_error_400(self, errors=None):
        if errors:
            return {'errors': errors}
        return {'errors': {'request': 'bad request'}}

    def build_error_404(self):
        return {'errors': {'id': 'record not found'}}

    def build_error_422(self, errors=None, to_dict=True):
        if errors:
            if to_dict and hasattr(errors, "as_dict"):
                errors = errors.as_dict()
            return {'errors': errors}
        return {'errors': {'request': 'unprocessable entity'}}

    def _build_meta(self, dbset, pagination, **kwargs):
        count = kwargs.get('count', dbset.count())
        page, page_size = pagination
        return {
            'object': 'list',
            'has_more': count > (page * page_size),
            'total_objects': count
        }

    def serialize(self, data, **extras):
        return _serialize(data, self.serializer, **extras)

    def serialize_with_list_envelope(self, data, dbset, pagination, **extras):
        return {self.list_envelope: self.serialize(data, **extras)}

    def serialize_with_list_envelope_and_meta(
        self, data, dbset, pagination, **extras
    ):
        mextras = extras.pop('meta_extras', {})
        return {
            self.list_envelope: self.serialize(data, **extras),
            self.meta_envelope: self.build_meta(dbset, pagination, **mextras)
        }

    def serialize_with_single_envelope(self, data, **extras):
        return {self.single_envelope: self.serialize(data, **extras)}

    def pack_with_list_envelope(self, envelope, data, **extras):
        return {envelope: data, **extras}

    def pack_with_list_envelope_and_meta(self, envelope, data, **extras):
        count = len(data)
        return {
            envelope: data,
            self.meta_envelope: self.build_meta(
                sdict(count=lambda c=count: c),
                (1, count)
            ),
            **extras
        }

    async def parse_params(self, *params):
        if params:
            rv = await _parse_params(*params, **self._parsing_params_kwargs)
        else:
            rv = await _parse_params_wparser(self.parser)
        for callback in self._after_params_callbacks:
            callback(rv)
        return rv

    #: default routes
    async def _index(self, dbset):
        pagination = self.get_pagination()
        sort = self.get_sort()
        rows = dbset.select(paginate=pagination, orderby=sort)
        return self.serialize_many(rows, dbset, pagination)

    async def _read(self, row):
        return self.serialize_one(row)

    async def _create(self):
        response.status = 201
        attrs = await self.parse_params()
        for callback in self._before_create_callbacks:
            callback(attrs)
        r = self.model.new(**attrs)
        if not r.save():
            response.status = 422
            return self.error_422(r.validation_errors, to_dict=False)
        for callback in self._after_create_callbacks:
            callback(r)
        return self.serialize_one(r)

    async def _create_without_save(self):
        response.status = 201
        attrs = await self.parse_params()
        for callback in self._before_create_callbacks:
            callback(attrs)
        r = self.model.create(**attrs)
        if r.errors:
            response.status = 422
            return self.error_422(r.errors)
        for callback in self._after_create_callbacks:
            callback(r.id)
        return self.serialize_one(r.id)

    async def _update(self, dbset, rid):
        r = dbset.where(self.model.table._id == rid).select().first()
        if not r:
            response.status = 404
            return self.error_404()
        attrs = await self.parse_params()
        for callback in self._before_update_callbacks:
            callback(r, attrs)
        r.update(**attrs)
        if not r.save():
            response.status = 422
            return self.error_422(r.validation_errors, to_dict=False)
        for callback in self._after_create_callbacks:
            callback(r)
        return self.serialize_one(r)

    async def _update_without_save(self, dbset, rid):
        attrs = await self.parse_params()
        for callback in self._before_update_callbacks:
            callback(rid, attrs)
        r = dbset.where(self.model.table._id == rid).validate_and_update(**attrs)
        if r.errors:
            response.status = 422
            return self.error_422(r.errors)
        elif not r.updated:
            response.status = 404
            return self.error_404()
        row = self.model.get(rid)
        for callback in self._after_update_callbacks:
            callback(row)
        return self.serialize_one(row)

    async def _delete(self, dbset, rid):
        r = dbset.where(self.model.table._id == rid).select().first()
        if not r or not r.destroy():
            response.status = 404
            return self.error_404()
        for callback in self._after_delete_callbacks:
            callback(r)
        return {}

    async def _delete_without_destroy(self, dbset, rid):
        r = dbset.where(self.model.table._id == rid).delete()
        if not r:
            response.status = 404
            return self.error_404()
        for callback in self._after_delete_callbacks:
            callback(rid)
        return {}

    #: additional routes
    async def _group(self, dbset, field):
        count_field = self.model.table._id.count()
        sort = self.get_sort(
            default='count',
            allowed_fields={'count': count_field}
        )
        data = [
            {
                'value': row[self.model.table][field.name],
                'count': row[count_field]
            } for row in dbset.select(
                field, count_field, groupby=field, orderby=sort
            )
        ]
        return self.pack_data(self.groups_envelope, data)

    async def _stats(self, dbset, fields):
        grouped_fields, select_fields, rv = {}, [], {}
        for field in fields:
            grouped_fields[field.name] = {
                'min': field.min(),
                'max': field.max(),
                'avg': field.avg()
            }
            select_fields.extend(grouped_fields[field.name].values())
        row = dbset.select(*select_fields).first()
        for key, attrs in grouped_fields.items():
            rv[key] = {
                attr_key: row[field] for attr_key, field in attrs.items()
            }
        return rv

    async def _sample(self, dbset):
        _, page_size = self.get_pagination()
        rows = dbset.select(paginate=(1, page_size), orderby='<random>')
        return self.serialize_many(
            rows, dbset, (1, page_size),
            meta_extras={'count': len(rows)}
        )

    #: properties
    @property
    def allowed_sorts(self) -> List[str]:
        return self._sortable_fields

    @allowed_sorts.setter
    def allowed_sorts(self, val: List[str]):
        self._sortable_fields = val
        self._sortable_dict = {
            field: self.model.table[field] for field in self._sortable_fields
        }

    @property
    def query_allowed_fields(self) -> List[str]:
        return self._queryable_fields

    @query_allowed_fields.setter
    def query_allowed_fields(self, val: List[str]):
        self._queryable_fields = val
        self._json_query_pipe.set_accepted()

    @property
    def grouping_allowed_fields(self) -> List[str]:
        return self._groupable_fields

    @grouping_allowed_fields.setter
    def grouping_allowed_fields(self, val: List[str]):
        self._groupable_fields = val
        self._group_field_pipe.set_accepted()

    @property
    def stats_allowed_fields(self) -> List[str]:
        return self._statsable_fields

    @stats_allowed_fields.setter
    def stats_allowed_fields(self, val: List[str]):
        self._statsable_fields = val
        self._stats_field_pipe.set_accepted()

    #: decorators
    def get_dbset(
        self,
        f: Callable[[RESTModule], DBSet]
    ) -> Callable[[RESTModule], DBSet]:
        self._fetcher_method = f
        return f

    def get_row(
        self,
        f: Callable[[DBSet], Optional[Row]]
    ) -> Callable[[DBSet], Optional[Row]]:
        self._select_method = f
        return f

    def before_create(
        self,
        f: Callable[[sdict], None]
    ) -> Callable[[sdict], None]:
        self._before_create_callbacks.append(f)
        return f

    def before_update(
        self,
        f: Callable[[int, sdict], None]
    ) -> Callable[[int, sdict], None]:
        self._before_update_callbacks.append(f)
        return f

    def after_parse_params(
        self,
        f: Callable[[sdict], None]
    ) -> Callable[[sdict], None]:
        self._after_params_callbacks.append(f)
        return f

    def after_create(self, f: Callable[[Row], None]) -> Callable[[Row], None]:
        self._after_create_callbacks.append(f)
        return f

    def after_update(self, f: Callable[[Row], None]) -> Callable[[Row], None]:
        self._after_update_callbacks.append(f)
        return f

    def after_delete(self, f: Callable[[int], None]) -> Callable[[int], None]:
        self._after_delete_callbacks.append(f)
        return f

    def index(self, pipeline=[]):
        pipeline = self.index_pipeline + pipeline
        return self.route(
            self._path_base, pipeline=pipeline, methods='get', name='index'
        )

    def read(self, pipeline=[]):
        pipeline = self.read_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods='get', name='read'
        )

    def create(self, pipeline=[]):
        pipeline = self.create_pipeline + pipeline
        return self.route(
            self._path_base, pipeline=pipeline, methods='post', name='create'
        )

    def update(self, pipeline=[]):
        pipeline = self.update_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods=['put', 'patch'],
            name='update'
        )

    def delete(self, pipeline=[]):
        pipeline = self.delete_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods='delete', name='delete'
        )

    def on_400(self, f):
        self.error_400 = f
        return f

    def on_404(self, f):
        self.error_404 = f
        return f

    def on_422(self, f):
        self.error_422 = f
        return f

    def meta_builder(self, f):
        self.build_meta = f
        return f
