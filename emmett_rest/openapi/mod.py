# -*- coding: utf-8 -*-
"""
    emmett_rest.openapi.mod
    -----------------------

    Provides OpenAPI application module

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from importlib.resources import read_text
from typing import Any, Dict, List, Optional, Union

from emmett import App, AppModule, response, url
from emmett.cache import RamCache, RouteCacheRule
from emmett.tools.service import JSONServicePipe
from emmett.utils import cachedprop

from ..rest import RESTModule
from .generation import build_schema
from .helpers import YAMLPipe


class OpenAPIModule(AppModule):
    def __init__(self,
        app: App,
        name: str,
        import_name: str,
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
        **kwargs: Any
    ):
        super().__init__(
            app,
            name,
            import_name,
            url_prefix=url_prefix,
            hostname=hostname,
            **kwargs
        )
        self._cache = RamCache()
        self.title = title
        self.description = description
        self.version = version
        self.tags = tags
        self.servers = servers
        self.terms_of_service = terms_of_service
        self.contact = contact
        self.license_info = license_info
        self.security_schemes = security_schemes
        self.produce_schemas = produce_schemas
        self.modules_list = []
        self.modules_tags = {}
        expose_ui = bool(app.debug) if expose_ui is None else expose_ui
        self._load_modules(modules_tree_prefix)
        self._define_routes(expose_ui, ui_path)

    def _load_modules(self, prefix: str):
        for key, mod in self.app._modules.items():
            if key.startswith(prefix) and isinstance(mod, RESTModule):
                self.modules_list.append(mod)
                self.modules_tags[mod.name] = mod.name.split(".")[-1].title()

    def _define_routes(self, expose_ui: bool, ui_path: str):
        self.route(
            "/openapi.json",
            name="schema_json",
            methods="get",
            pipeline=[JSONServicePipe()],
            cache=RouteCacheRule(self._cache) if not bool(self.app.debug) else None
        )(self._get_spec)
        self.route(
            "/openapi.yaml",
            name="schema_yaml",
            methods="get",
            pipeline=[YAMLPipe()],
            cache=RouteCacheRule(self._cache) if not bool(self.app.debug) else None
        )(self._get_spec)
        if expose_ui:
            self.route(
                ui_path,
                name="ui",
                methods="get",
                output="str",
                cache=RouteCacheRule(self._cache) if not bool(self.app.debug) else None
            )(self._ui_stoplight)

    async def _get_spec(self):
        return build_schema(
            title=self.title,
            version=self.version,
            description=self.description or self._default_description,
            modules=self.modules_list,
            modules_tags=self.modules_tags,
            produce_schemas=self.produce_schemas,
            tags=self.tags,
            servers=self.servers,
            terms_of_service=self.terms_of_service,
            contact=self.contact,
            license_info=self.license_info,
            security_schemes=self.security_schemes
        )

    @cachedprop
    def _stoplight_template(self):
        return read_text("emmett_rest.openapi.assets", "stoplight.html")

    @cachedprop
    def _default_description(self):
        return self.app.templater._render(
            read_text("emmett_rest.openapi.assets", "description.md"),
            file_path="__emmett_rest__/openapi/description.md",
            context={
                "title": self.title,
            }
        )

    async def _ui_stoplight(self):
        response.content_type = "text/html; charset=utf-8"
        return self.app.templater._render(
            self._stoplight_template,
            file_path="__emmett_rest__/openapi/stoplight.html",
            context={
                "title": self.title,
                "openapi_url": url(f"{self.name}.schema_yaml")
            }
        )

    def regroup(self, module_name: str, destination: str):
        self.modules_tags[module_name] = self.modules_tags[destination]
