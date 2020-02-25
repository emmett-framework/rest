# -*- coding: utf-8 -*-

import pytest

from emmett.orm import Field, Model


class Sample(Model):
    str = Field()


@pytest.fixture(scope='function')
def db(migration_db):
    return migration_db(Sample)


@pytest.fixture(scope='function')
def rest_app(app, db):
    app.pipeline = [db.pipe]
    return app


@pytest.fixture(scope='function', autouse=True)
def db_sample(db):
    with db.connection():
        Sample.create(str='foo')


@pytest.fixture(scope='function')
def client_default(rest_app):
    rest_app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample'
    )
    return rest_app.test_client()


@pytest.fixture(scope='function')
def client_envelopes(rest_app):
    rest_app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample',
        single_envelope='sample', list_envelope='samples',
        use_envelope_on_parse=True
    )
    return rest_app.test_client()


def test_default_index(client_default, json_load):
    req = client_default.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data', 'meta'} == set(data.keys())


def test_default_get(client_default, json_load, db):
    with db.connection():
        row = Sample.first()

    req = client_default.get(f'/sample/{row.id}')
    assert req.status == 200

    data = json_load(req.data)
    assert {'id', 'str'} == set(data.keys())


def test_envelopes_index(client_envelopes, json_load):
    req = client_envelopes.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'samples', 'meta'} == set(data.keys())


def test_envelopes_get(client_envelopes, json_load, db):
    with db.connection():
        row = Sample.first()

    req = client_envelopes.get(f'/sample/{row.id}')
    assert req.status == 200

    data = json_load(req.data)
    assert {'sample'} == set(data.keys())


def test_envelopes_create(client_envelopes, json_load, json_dump):
    req = client_envelopes.post(
        '/sample',
        data=json_dump({'sample': {'str': 'foo'}}),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 201

    data = json_load(req.data)
    assert {'sample'} == set(data.keys())
    assert data['sample']['id']


def test_envelopes_update(client_envelopes, json_load, json_dump):
    req = client_envelopes.post(
        '/sample',
        data=json_dump({'sample': {'str': 'foo'}}),
        headers=[('content-type', 'application/json')]
    )
    data = json_load(req.data)
    rid = data['sample']['id']

    req = client_envelopes.put(
        f'/sample/{rid}',
        data=json_dump({'sample': {'str': 'baz'}}),
        headers=[('content-type', 'application/json')]
    )
    assert req.status == 200

    data = json_load(req.data)
    assert data['sample']['str'] == 'baz'
