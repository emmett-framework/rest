# -*- coding: utf-8 -*-

import pytest

from emmett.orm import Field, Model


class Sample(Model):
    str = Field()
    int = Field.int(default=0)
    float = Field.float(default=0.0)


@pytest.fixture(scope='function')
def db(migration_db):
    return migration_db(Sample)


@pytest.fixture(scope='function')
def rest_app(app, db):
    app.pipeline = [db.pipe]
    mod = app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample',
        enabled_methods=['group', 'stats', 'sample']
    )
    mod.grouping_allowed_fields = ['str']
    mod.stats_allowed_fields = ['int', 'float']
    return app


@pytest.fixture(scope='function', autouse=True)
def db_sample(db):
    with db.connection():
        Sample.create(str='foo')
        Sample.create(str='foo', int=5, float=5.0)
        Sample.create(str='bar', int=10, float=10.0)


@pytest.fixture(scope='function')
def client(rest_app):
    return rest_app.test_client()


def test_grouping(client, json_load):
    req = client.get('/sample/group/str', query_string={'sort_by': '-count'})
    assert req.status == 200

    data = json_load(req.data)
    assert data['meta']['total_objects'] == 2

    assert data['data'][0]['value'] == 'foo'
    assert data['data'][0]['count'] == 2
    assert data['data'][1]['value'] == 'bar'
    assert data['data'][1]['count'] == 1


def test_stats(client, json_load):
    req = client.get('/sample/stats', query_string={'fields': 'int,float'})
    assert req.status == 200

    data = json_load(req.data)
    assert data['int']['min'] == 0
    assert data['int']['max'] == 10
    assert data['int']['avg'] == 5
    assert data['float']['min'] == 0.0
    assert data['float']['max'] == 10.0
    assert data['float']['avg'] == 5.0


def test_sample(client, json_load):
    req = client.get('/sample/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert data['meta']['total_objects'] == 3
    assert not data['meta']['has_more']
