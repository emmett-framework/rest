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
    app.rest_module(__name__, 'sample', Sample, url_prefix='sample')
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


def test_create(client, json_load, json_dump):
    body = sdict(
        str='bar',
        int=2,
        float=1.1,
        datetime=datetime(2000, 1, 1)
    )
    req = client.post(
        '/sample',
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
        '/sample',
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['int']


def test_update(client, json_load, json_dump):
    body = sdict(
        str='bar',
        int=2,
        float=1.1,
        datetime=datetime(2000, 1, 1)
    )
    req = client.post(
        '/sample',
        data=json_dump(body),
        headers=[('content-type', 'application/json')]
    )

    data = json_load(req.data)
    rid = data['id']

    change = sdict(
        str='baz'
    )
    req = client.put(
        f'/sample/{rid}',
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
        f'/sample/{rid}',
        data=json_dump(change),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 422

    data = json_load(req.data)
    assert data['errors']['int']


def test_delete(client, db):
    with db.connection():
        row = Sample.first()

    req = client.delete(
        f'/sample/{row.id}',
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    with db.connection():
        assert not Sample.all().count()
