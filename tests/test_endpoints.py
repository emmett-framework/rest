# -*- coding: utf-8 -*-

import pytest

from datetime import datetime
from emmett import sdict
from emmett.orm import Field, Model


class Sample(Model):
    str = Field()
    int = Field.int()
    float = Field.float()
    datetime = Field.datetime()


@pytest.fixture(scope='function')
def db(migration_db):
    return migration_db(Sample)


@pytest.fixture(scope='function')
def rest_app(app, db):
    app.pipeline = [db.pipe]
    app.rest_module(
        __name__, 'sample', Sample,
        url_prefix='sample'
    )
    app.rest_module(
        __name__, 'sample_row', Sample,
        url_prefix='sample_row', use_save=True, use_destroy=True
    )
    return app


@pytest.fixture(scope='function', autouse=True)
def db_sample(db):
    with db.connection():
        Sample.create(
            str='foo',
            int=1,
            float=3.14,
            datetime=datetime(1955, 11, 12)
        )


@pytest.fixture(scope='function')
def client(rest_app):
    return rest_app.test_client()


def test_modules(rest_app):
    mod1 = rest_app._modules['sample']
    mod2 = rest_app._modules['sample_row']

    assert mod1._functions_map['create'] == '_create_without_save'
    assert mod1._functions_map['update'] == '_update_without_save'
    assert mod1._functions_map['delete'] == '_delete_without_destroy'

    assert mod2._functions_map['create'] == '_create'
    assert mod2._functions_map['update'] == '_update'
    assert mod2._functions_map['delete'] == '_delete'


def test_index(client, json_load):
    req = client.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data', 'meta'} == set(data.keys())
    assert {'id', 'str', 'int', 'float', 'datetime'} == set(
        data['data'][0].keys())
    assert data['meta']['total_objects'] == 1
    assert not data['meta']['has_more']


def test_get(client, json_load, db):
    with db.connection():
        row = Sample.first()

    req = client.get(f'/sample/{row.id}')
    assert req.status == 200

    data = json_load(req.data)
    assert {'id', 'str', 'int', 'float', 'datetime'} == set(
        data.keys())


@pytest.mark.parametrize("base_path", ["/sample", "/sample_row"])
def test_create(client, json_load, json_dump, base_path):
    body = sdict(
        str='bar',
        int=2,
        float=1.1,
        datetime=datetime(2000, 1, 1)
    )
    req = client.post(
        base_path,
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 201

    data = json_load(req.data)
    assert data['id']
    assert data['str'] == 'bar'

    #: validation tests
    body = sdict(
        str='bar',
        int='foo',
        float=1.1,
        datetime=datetime(2000, 1, 1)
    )
    req = client.post(
        base_path,
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['int']


@pytest.mark.parametrize("base_path", ["/sample", "/sample_row"])
def test_update(client, json_load, json_dump, base_path):
    body = sdict(
        str='bar',
        int=2,
        float=1.1,
        datetime=datetime(2000, 1, 1)
    )
    req = client.post(
        base_path,
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )

    data = json_load(req.data)
    rid = data['id']

    change = sdict(
        str='baz'
    )
    req = client.put(
        f'{base_path}/{rid}',
        data=json_dump(change),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    data = json_load(req.data)
    assert data['str'] == 'baz'

    #: validation tests
    change = sdict(
        int='baz'
    )
    req = client.put(
        f'{base_path}/{rid}',
        data=json_dump(change),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['int']


@pytest.mark.parametrize("base_path", ["/sample", "/sample_row"])
def test_delete(client, db, base_path):
    with db.connection():
        row = Sample.first()

    req = client.delete(
        f'{base_path}/{row.id}',
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    with db.connection():
        assert not Sample.all().count()
