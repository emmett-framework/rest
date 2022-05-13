# Emmett-REST

Emmett-REST is a REST extension for [Emmett framework](https://emmett.sh).

[![pip version](https://img.shields.io/pypi/v/emmett-rest.svg?style=flat)](https://pypi.python.org/pypi/Emmett-REST)
![Tests Status](https://github.com/emmett-framework/rest/workflows/Tests/badge.svg)

## In a nutshell

```python
from emmett.orm import Model, Field
from emmett_rest import REST

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()

app.use_extension(REST)

tasks = app.rest_module(__name__, 'api_task', Task, url_prefix='tasks')
tasks.query_allowed_fields = ['is_completed']
```

Output of `http://{host}/tasks?where={"is_completed": false}`:

```json
{
    "meta": {
        "object": "list",
        "total_objects": 1,
        "has_more": false
    },
    "data": [
        {
            "title": "Some task",
            "is_completed": false
        }
    ]
}
```

## Installation

You can install Emmett-REST using pip:

    pip install Emmett-REST

And add it to your Emmett application:

```python
from emmett_rest import REST

rest = app.use_extension(REST)
```

## Usage

The Emmett-REST extension is intended to be used with Emmett [models](https://emmett.sh/docs/latest/orm/models), and it uses application modules to build APIs over them. 

Let's say, for example, that you have a task manager app with a `Task` model:

```python
from emmett.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    spent_time = Field.int()
    created_at = Field.datetime()
```

Then, in order to expose REST apis for your `Task` model, you can use the `rest_module` method on your application or on any application module:

```python
from myapp import app, Task

tasks = app.rest_module(__name__, 'api_task', Task, url_prefix='tasks')
```

As you can see, the usage is very similar to the Emmett application modules, but we also passed the involved model to the module initialization.

This single line is enough to have a really simple REST api over the `Task` model, since under the default behaviour rest modules will expose 5 different routes:

- an *index* route that will respond to `GET` requests on `/tasks` path listing all the tasks in the database
- a *read* route that will respond to `GET` requests on `/tasks/<int:rid>` path returning a single task corresponding to the record id of the *rid* variable
- a *create* route that will respond to `POST` requests on `/tasks` that will create a new task in the database
- an *update* route that will respond to `PUT` or `PATCH` requests on `/tasks/<int:rid>` that will update the task corresponding to the record id of the *rid* variable
- a *delete* route that will respond to `DELETE` requests on `/tasks/<int:rid>` that will delete the task corresponding to the record id of the *rid* variable.

Listing endpoints accepts some query parameters by default, and specifically:

| parameter | default | description |
| --- | --- | --- |
| page | 1 | page to return |
| page\_size | 20 | number of records per page to return|
| sort\_by | id | field to sort records by (-field for desc) |
| where | {} | json dumped string for querying |

### Additional routes

Emmett-REST also provides some additional not CRUD endpoints. Let's see them specifically. 

#### Sample route

It behaves like the *index* route, but gets records randomly. As a consequence, the `sort_by` parameter gets ignored.

Responds to `GET` requests on `{base_path}/sample` endpoint, and can be activated adding `'sample'` to the enabled methods on module definition or in the extension settings.

#### Grouping route

Responds to `GET` requests on `{base_path}/group/<str:field>` endpoint, and can be activated adding `'group'` to the enabled methods on module definition or in the extension settings.

It groups by value and count records for the given field. Results of calling `http://{host}/tasks/group/is_completed` looks like:

```json
{
    "meta": {
        "object": "list",
        "total_objects": 11,
        "has_more": false
    },
    "data": [
        {
            "value": true,
            "count": 1
        },
        {
            "value": false,
            "count": 10
        }
    ]
}
```

#### Stats route

Responds to `GET` requests on `{base_path}/stats` endpoint, and can be activated adding `'stats'` to the enabled methods on module definition or in the extension settings. Parse a list of fields from the comma separated `fields` query parameter.

It return minimum, maximum and average values of the records for the specified fields. Results of calling `http://{host}/tasks/stats?fields=spent_time` looks like:

```json
{
    "spent_time": {
        "min": 0,
        "max": 3600,
        "avg": 27
    }
}
```

### REST module parameters

The `rest_module` method accepts several parameters (*bold ones are required*) for its configuration:

| parameter | default | description |
| --- | --- | --- |
| **import_name** | | as for standard modules |
| **name** | | as for standard modules |
| **model** | | the model to use |
| serializer | `None` | a class to be used for serialization |
| parser | `None` | a class to be used for parsing |
| enabled\_methods | `str` list: index, create, read, update, delete | the routes that should be enabled on the module |
| disabled\_methods | `[]` | the routes that should be disabled on the module |
| default\_sort | `None` | the field used for sorting records by default (use model primary key unless specified) |
| use\_save | `True` | whether to use the `save` method in records to perform operations or the low-level ORM APIs |
| use\_destroy | `True` | whether to use the `destroy` method in records to perform operations or the low-level ORM APIs |
| list\_envelope | data | the envelope to use on the index route |
| single\_envelope | `False` | the envelope to use on all the routes except for lists endpoints |
| meta\_envelope | meta | the envelope to use for meta data |
| groups\_envelope | data | the envelope to use for the grouping endpoint |
| use\_envelope\_on\_parse | `False` | if set to `True` will use the envelope specified in *single_envelope* option also on parsing |
| serialize\_meta | `True` | whether to serialize meta data on lists endpoint |
| base\_path | `/` | the default path prefix for routes not involving a single record |
| id\_path | `/<int:rid>` | the default path prefix for routes involving a single record |
| url\_prefix | `None` | as for standard modules |
| hostname | `None` | as for standard modules |
| module\_class | `RestModule` | the module class to use |

### REST module properties

Some of the REST module parameters needs to be configured using attributes, specifically:

| attribute | description |
| --- | --- |
| allowed\_sorts | list of fields that can be used with `sort_by` parameter |
| query\_allowed\_fields | list of fields that can be used with `where` parameter |
| grouping\_allowed\_fields | list of fields that can be used in `group` route |
| stats\_allowed\_fields | list of fields that can be used in `stats` route |

An example would be:

```python
tasks.allowed_sorts = ['id', 'created_at']
tasks.query_allowed_fields = ['is_completed']
tasks.grouping_allowed_fields = ['is_completed']
tasks.stats_allowed_fields ['time_spent']
```

### Customizing the database set

Under default behavior, any REST module will use `Model.all()` as the database set on every operation.

When you need to customize it, you can use the `get_dbset` decorator. 
For example, you may gonna use the Emmett auth module:

```python
from myapp import auth

@tasks.get_dbset
def fetch_tasks():
    return auth.user.tasks
```

or you may have some soft-deletions strategies and want to expose just the records which are not deleted:

```python
@tasks.get_dbset
def fetch_tasks():
    return Task.where(lambda t: t.is_deleted == False)
```

### Customizing single row fetching

Under default behaviour, any REST module will use standard select to fetch the record on the `read` endpoint.

When you need to customize it, you can use the `get_row` decorator.

For example, you may want to add a left join to the selection:

```python
@tasks.get_row
def fetch_row(dbset):
    return dbset.select(
        including=['many_relation'], limitby=(0, 1)
    ).first()
```

### Customizing routed methods

You can customize every route of the REST module using its `index`, `create`, `read`, `update` and `delete` decorators. In the next examples we'll override the routes with the default ones, in order to show the original code behind the default routes.

```python
from emmett import request

@tasks.index()
async def task_list(dbset):
    pagination = tasks.get_pagination()
    sort = tasks.get_sort()
    rows = dbset.select(paginate=pagination, orderby=sort)
    return tasks.serialize_many(rows, dbset, pagination)
```

As you can see, an *index* method should accept the `dbset` parameter, that is injected by the module. This is the default one or the one you defined with the `get_dbset` decorator.

```python
@tasks.read()
async def task_single(row):
    return tasks.serialize_one(row)
```

The *read* method should accept the `row` parameter that is injected by the module. Under default behaviour the module won't call your method if it doesn't find the requested record, but instead will return a 404 HTTP response.

```python
@tasks.create()
async def task_new():
    response.status = 201
    attrs = await tasks.parse_params()
    row = Task.new(**attrs)
    if not row.save()::
        response.status = 422
        return tasks.error_422(row.validation_errors)
    return tasks.serialize_one(row)
```

The *create* method won't need any parameters, and is responsible of creating new records in the database.

> **Note:** since Emmett 2.4, a `save` method is available on records. Emmett-REST acts accordingly to the `use_save` configuration parameter (in extension configuration or module initialization), using `Model.create` when saving is disabled.

The *update* and *delete* methods are quite similar:

```python
@tasks.update()
async def task_edit(dbset, rid):
    attrs = await tasks.parse_params()
    row = dbset.where(Task.id == rid).select().first()
    if not row:
        response.status = 404
        return tasks.error_404()
    row.update(**attrs)
    if not row.save():
        response.status = 422
        return tasks.error_422(row.validation_errors)
    return tasks.serialize_one(row)
```

```python
@tasks.delete()
async def task_del(dbset, rid):
    row = dbset.where(Task.id == rid).select().first()
    if not row or not row.destroy():
        response.status = 404
        return self.error_404()
    return {}
```

since, as you can see, they should accept the `dbset` parameter and the `rid` one, which will be the record id requested by the client.

> **Note:** since Emmett 2.4, `save` and `destroy` method are available on records. Emmett-REST acts accordingly to the `use_save` and `use_destroy` configuration parameter (in extension configuration or module initialization), using `dbset.update` and `dbset.delete` when saving and/or destroying is disabled.

All the decorators accept an additional `pipeline` parameter that you can use to add custom pipes to the routed function:

```python
@tasks.index(pipeline=[MyCustomPipe()])
def task_index:
    # code
```

### Customizing errors

You can define custom methods for the HTTP 400, 404 and 422 errors that will generate the JSON output using the `on_400`, `on_404` and `on_422` decorators:

```python
@tasks.on_400
def task_400err():
    return {'error': 'this is my 400 error'}

@tasks.on_404
def task_404err():
    return {'error': 'this is my 404 error'}
    
@tasks.on_422
def task_422err(errors):
    return {'error': 422, 'validation': errors}
```

### Customizing meta generation

You can define custom method for the `meta` generation using the appropriate `meta_builder` decorator:

```python
@tasks.meta_builder
def _tasks_meta(self, dbset, pagination):
    count = dbset.count()
    page, page_size = pagination
    total_pages = math.ceil(count / page_size)
    return {
        'page': page,
        'page_prev': page - 1 if page > 1 else None,
        'page_next': page + 1 if page < total_pages else None,
        'total_pages': total_pages,
        'total_objects': count
    }
```

### Serialization

Under the default behaviour, the REST extension will use the `fields_rw` attribute of the involved model, and overwrite the results with the contents of the `rest_rw` attribute if present.

For example, with this model:

```python
from emmett.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    fields_rw = {
        'id': False,
        'created_at': False
    }
```

the REST extension will serialize just the *title* and the *is_completed* fields, while with this:

```python
from emmett.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    fields_rw = {
        'id': False,
        'created_at': False
    }
    
    rest_rw = {
        'id': True
    }
```

the REST extension will serialize also the *id* field.

#### Serializers

Whenever you need more control over the serialization, you can use the `Serializer` class of the REST extension:

```python
from emmett_rest import Serializer

class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
tasks = app.rest_module(
    __name__, 'api_task', Task, serializer=TaskSerializer, url_prefix='tasks')
```

Serializers are handy when you want to add custom function to serialize something present in your rows. For instance, let's say you have a very simple tagging system:

```python
from emmett.orm import belongs_to, has_many

class Task(Model):
    has_many({'tags': 'TaskTag'})

class TaskTag(Model):
    belongs_to('task')
    name = Field.string()
```

and you want to serialize the tags as an embedded list in your task. Then you just have to add a `tags` method to your serializer:

```python
class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
    def tags(self, row):
        return row.tags().column('name')
```

This is the complete list of rules that the extension will take over serializers:

- `attributes` is read as first step
- the `fields_rw` and `rest_rw` attributes of the model are used to fill `attributes` list when this is empty
- the fields in the `include` list will be added to `attributes`
- the fields in the `exclude` list will be removed from `attributes`
- every method defined in the serializer not starting with `_` will be called over serialization and its return value will be added to the JSON object in a key named as the method

You can also use different serialization for the list route and the other ones:

```python
from emmett_rest import Serializer, serialize

class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
class TaskDetailSerializer(TaskSerializer):
    include = ['is_completed']
    
tasks = app.module(
    __name__, 'api_task', Task, 
    serializer=TaskDetailSerializer, url_prefix='tasks')

@tasks.index()
def task_list(dbset):
    rows = dbset.select(paginate=tasks.get_pagination())
    return serialize(rows, TaskSerializer)
```

> **Note:** under default behaviour the `serialize` method will use the serializer passed to the module.

### Parsing input

Opposite to the serialization, you will have input parsing to parse JSON requests and perform operations on the records.

Under the default behaviour, the REST extension will use the `fields_rw` attribute of the involved model, and overwrite the results with the contents of the `rest_rw` attribute if present.

For example, with this model:

```python
from emmett.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    fields_rw = {
        'id': False,
        'created_at': False
    }
```

the REST extension will parse the input to allow just the *title* and the *is_completed* fields, while with this:

```python
from emmett.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    fields_rw = {
        'id': False,
        'created_at': False
    }
    
    rest_rw = {
        'id': (True, False)
        'created_at': True
    }
```

the REST extension will allow also the *created_at* field.

#### Parsers

Very similarly to the `Serializer` class, the extension provides also a `Parser` one:

```python
from emmett_rest import Parser

class TaskParser(Parser):
    attributes = ['title']
    
tasks = app.rest_module(
    __name__, app, 'api_task', Task, parser=TaskParser, url_prefix='tasks')
```

As for serializers, you can define `attributes`, `include` and `exclude` lists in a parser, and add custom methods that will parse the params:

```python
class TaskParser(Parser):
    attributes = ['title']
    
    def created_at(self, params):
        # some code
```

and you also have the `envelope` attribute at your disposal in case you expect to have enveloped bodies over `POST`, `PUT` and `PATCH` requests:

```python
class TaskParser(Parser):
    envelope = "task"
```

The `Parser` class also offers some decorators you might need in your code: `parse_value` and `processor`.

While the first one might be handy in conditions where you need to edit a single attribute:

```python
class TaskParser(Parser):
    _completed_map = {"yes": True, "no": False}

    @Parser.parse_value("is_completed")
    def parse_completed(self, value):
        return self._completed_map[value]
```

the latter gives you access to all the parameters and the parsed dictionary, so you can deeply customise the parsing flow:

```python
class TaskParser(Parser):
    @Parser.processor()
    def custom_parsing(self, params, obj):
        obj.status = "completed" if params.is_completed else "running"
```

### Pagination

REST modules perform pagination over the listing routes under the default behaviour. This is performed with the `paginate` option during the select and the call to the `get_pagination` method.

You can customize the name of the query params or the default page sizes with the extension configuration, or you can override the method completely with subclassing.

### Callbacks

Unless overridden, the default `create`, `update` and `delete` methods invoke callbacks you can attach to the module using the approriate decorator. Here is the complete list:

| callback | arguments| description |
| --- | --- | --- |
| before\_create | `[sdict]` | called before the record insertion |
| before\_update | `[id\|Row, sdict]` | called before the record gets update (when saving is disabled, the first argument is the id of the record, otherwise the record to be updated) |
| after\_parse\_params | `[sdict]` | called after params are loaded from the request body |
| after\_create | `[Row]` | called after the record insertion |
| after\_update | `[Row]` | called after the record gets updated |
| after\_delete | `[id\|Row]` | called after the record gets deleted (when destroying is disabled, the argument is the id of the record, otherwise the destroyed record) |

For example, you might need to notify some changes:

```python
@tasks.after_create
def _notify_task_creation(row):
    my_publishing_system.notify(
        f"Task {row['title']} was added"
    )
```

### Query language

The `where` query parameter allow, within the fields specified in `query_allowed_fields`, to query records in the listing routes using a JSON object.

The query language is inspired to the MongoDB query language, and provides the following operators:

| operator | argument type | description |
| --- | --- | --- |
| $and | `List[Dict[str, Any]]` | logical AND |
| $or | `List[Dict[str, Any]]` | logical OR |
| $not | `Dict[str, Any]` | logical NOT |
| $eq | `Any` | matches specified value |
| $ne | `Any` | inverse of $eq |
| $in | `List[Any]` | matches any of the values in list |
| $nin | `List[Any]` | inverse of $in |
| $lt | `Union[int, float, str]` | matches values less than specified value |
| $gt | `Union[int, float, str]` | matches values greater than specified value |
| $le | `Union[int, float, str]` | matches values less than or equal to specified value |
| $ge | `Union[int, float, str]` | matches values greater than or equal to specified value |
| $exists | `bool` | matches not null or null values |
| $like | `str` | matches specified like expression |
| $ilike | `str` | case insensitive $like |
| $contains | `str` | matches values containing specified value |
| $icontains | `str` | case insensitive $contains |
| $geo.contains | `GeoDict` | GIS `ST_Contains` |
| $geo.equals | `GeoDict` | GIS `ST_Equals` |
| $geo.intersects | `GeoDict` | GIS `ST_Intersects` |
| $geo.overlaps | `GeoDict` | GIS `ST_Overlaps` |
| $geo.touches | `GeoDict` | GIS `ST_Touches` |
| $geo.within | `GeoDict` | GIS `ST_Within` |
| $geo.dwithin | `GeoDistanceDict` | GIS `ST_DWithin` |

where `GeoDict` indicates a dictionary with a `type` key indicating the geometry type and `coordinates` array containing the geometry points (eg: `{"type": "point", "coordinates": [1, 2]}`), while `GeoDistanceDict` indicates a dictionary with a `geometry` key containing a `GeoDict` and the `distance` one (eg: `{"geometry": {"type": "point", "coordinates": [1, 2]}, "distance": 5}`).

The JSON condition always have fields' names as keys (except for `$and`, `$or`, `$not`) and operators as values, where `$eq` is the default one:

```json
{
    "is_completed": false,
    "priority": {"$gte": 5}
}
```

### OpenAPI schemas

Emmett-REST provides utilities to automatically generate OpenAPI schemas and relevant UI.

In order to produce JSON and YAML schemas, you can instantiate a `docs` module:

```python
docs = rest.docs_module(
    __name__,
    "api_docs",
    title="My APIs",
    version="1",
    modules_tree_prefix="api.v1"
)
```

As you can see, the `docs_module` methods requires a `modules_tree_prefix` parameter which instructs REST extensions which modules should be included in the schema.

> **Note:** ensure to define your REST modules before instantiating the OpenAPI one, as the latter will need modules to be pre-defined in order to make the inspection.

The `docs_module` method accepts several parameters (*bold ones are required*) for its configuration:

| parameter | default | description |
| --- | --- | --- |
| **import_name** | | as for standard modules |
| **name** | | as for standard modules |
| **title** | | the title for the OpenAPI schema |
| **version** | | version for the OpenAPI schema |
| **modules\_tree\_prefix** | | a prefix for modules names to be included in the schema |
| description | `None` | general description for the schema |
| tags | `None` | tags for the schema |
| servers | `None` | servers for the schema |
| terms\_of\_service | `None` | terms of service for the schema |
| contact | `None` | contact information for the schema |
| license\_info | `None` | license information for the schema |
| security\_schemes | `None` | security information for the schema |
| produce\_schemas | `False` | wheter to generate OpenAPI *schema* resources from modules serializers in addition to endpoints |
| expose\_ui | `None` | wheter to expose UI (under default behaviour will match the application debug flag) |
| ui\_path | `/docs` | path for the UI component |
| url\_prefix | `None` | as for standard modules |
| hostname | `None` | as for standard modules |

Under default behaviour, Emmett-REST will generate OpenAPI schema considering your modules endpoints, inferring types from your models, serializers and parsers.

#### Customising endpoints grouping

Under default behaviour, endpoints in generated OpenAPI schema are grouped by module. In case you need to change this, you can use the docs module `regroup` method:

```python
docs.regroup("api.v1.some_module", "api.v1.another_module")
```

#### OpenAPI modules' methods

Emmett-REST provides an `openapi` object in your REST modules to enable schema customisations. Specifically, this allows you to customise naming, serializers and parsers specs for your module methods:

- `RESTModule.openapi.describe.entity(name)` lets you specify a custom name for the module entity
- `RESTModule.openapi.define.serializer(Serializer, methods)` lets you specify different serialization specs for the given methods
- `RESTModule.openapi.define.parser(Parser, methods)` lets you specify different deserialization specs for the given methods

#### OpenAPI decorators

Emmett-REST provides an `openapi` decorator to allow definition of additional routes and customisation of OpenAPI schema. Let's see them in detail.

##### include

Used to include a custom route in the resulting OpenAPI schema:

```python
from emmett_rest.openapi import openapi

@mymodule.route()
@openapi.include
async def custom_method():
    ...
```

##### define

Used to specify schemes and attributes in different contexts. The `define` group provides several decorators with specific use-cases:

- `openapi.define.fields` let you specify the type and default values on serializers and parsers for conditions where such data cannot be directly inferred
- `openapi.define.request` let you specify request specs on custom endpoints
- `openapi.define.response` let you specify response specs on custom endpoints
- `openapi.define.response_default_errors` let you re-use standard response errors on custom endpoints
- `openapi.define.serializer` let you re-use a `Serializer` spec on custom endpoints
- `openapi.define.parser` let you re-use a `Parser` spec on custom endpoints

##### describe

Used to describe OpenAPI schemes in different contexts. The `describe` group provides several decorators with specific use-cases:

- `openapi.describe` let you specify a summary and description on custom endpoints
- `openapi.describe.summary` let you specify a summary for custom endpoints
- `openapi.describe.description` let you specify a description for custom endpoints
- `openapi.describe.request` let you specify descriptions for request schemes
- `openapi.describe.response` let you specify descriptions for response schemes

### Customizing REST modules

#### Extension options

This is the list of all the configuration variables available on the extension for customization – the default values are set:

```python
app.config.REST.default_module_class = RESTModule
app.config.REST.default_serializer = Serializer
app.config.REST.default_parser = Parser
app.config.REST.page_param = 'page'
app.config.REST.pagesize_param = 'page_size'
app.config.REST.sort_param = 'sort_by'
app.config.REST.query_param = 'where'
app.config.REST.min_pagesize = 10
app.config.REST.max_pagesize = 25
app.config.REST.default_pagesize = 20
app.config.REST.default_sort = None
app.config.REST.base_path = '/'
app.config.REST.id_path = '/<int:rid>'
app.config.REST.list_envelope = 'data'
app.config.REST.single_envelope = False
app.config.REST.groups_envelope = 'data'
app.config.REST.use_envelope_on_parse = False
app.config.REST.serialize_meta = True
app.config.REST.meta_envelope = 'meta'
app.config.REST.default_enabled_methods = [
    'index',
    'create',
    'read',
    'update',
    'delete'
]
app.config.REST.default_disabled_methods = []
app.config.REST.use_save = True
app.config.REST.use_destroy = True
```

This configuration will be used by all the REST modules you create, unless overridden.

#### Subclassing

Under the default behavior, every REST module will use the `RESTModule` class. You can create as many subclasses from this one when you need to apply the same behaviour to several modules:

```python
from emmett_rest import RESTModule

class MyRESTModule(RESTModule):
    def init(self):
        self.disabled_methods = ['delete']
        self.index_pipeline.append(MyCustomPipe())
        self.list_envelope = 'objects'
        self.single_envelope = self.model.__name__.lower()
        
    def _get_dbset(self):
        return self.model.where(lambda m: m.user == session.user.id)
        
    async def _index(self, dbset):
        rows = dbset.select(paginate=self.get_pagination())
        rv = self.serialize_many(rows)
        rv['meta'] = {'total': dbset.count()}
        return rv
        
tasks = app.rest_module(
    __name__, app, 'api_task', Task, url_prefix='tasks', 
    module_class=MyRESTModule)
tags = app.rest_module(
    __name__, app, 'api_tag', Tag, url_prefix='tags',
    module_class=MyRESTModule)
```

As you can see, we defined a subclass of the `RESTModule` one and used the `init` method to customize the class initialization for our needs. We **strongly** recommend to use this method and avoid overriding the `__init__` of the class unless you really know what you're doing.

Using the `init` method, we disabled the *delete* route over the module, added a custom pipe over the *index* route and configured the envelope rules.

Here is a list of variables you may want to change inside the `init` method:

- model
- serializer
- parser
- enabled\_methods
- disabled\_methods
- list\_envelope
- single\_envelope
- meta\_envelope
- groups\_envelope
- use\_envelope\_on\_parsing

Also, this is the complete list of the pipeline variables and their default values:

```python
def init(self):
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
```

We've also overridden the methods for the database set retrieval and the *index* route. As you can see, these methods are starting with the `_` since are the default ones and you can still override them with decorators. This is the complete list of methods you may want to override instead of using decorators:

- `_get_dbset`
- `_get_row` 
- `_index`
- `_create`
- `_read`
- `_update`
- `_delete`
- `_group`
- `_stats`
- `_sample`
- `_build_meta`
- `build_error_400`
- `build_error_404`
- `build_error_422`

There are some other methods you may need to override, like the `get_pagination` one or the serialization ones. Please, check the source code of the `RESTModule` class for further needs.

## License

Emmett-REST is released under BSD license. Check the LICENSE file for more details.
