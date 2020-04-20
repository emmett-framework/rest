# -*- coding: utf-8 -*-

import math
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
def client_meta(rest_app):
    rest_app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample'
    )
    return rest_app.test_client()


@pytest.fixture(scope='function')
def client_nometa(rest_app):
    rest_app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample',
        serialize_meta=False
    )
    return rest_app.test_client()


@pytest.fixture(scope='function')
def client_metacustom(rest_app):
    mod = rest_app.rest_module(
        __name__, 'sample', Sample, url_prefix='sample'
    )

    @mod.meta_builder
    def _meta(dbset, pagination, **kwargs):
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

    return rest_app.test_client()


def test_meta_index(client_meta, json_load):
    req = client_meta.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data', 'meta'} == set(data.keys())
    assert data['meta']['object'] == 'list'
    assert data['meta']['total_objects'] == 1
    assert not data['meta']['has_more']


def test_nometa_index(client_nometa, json_load):
    req = client_nometa.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data'} == set(data.keys())


def test_metacustom_index(client_metacustom, json_load):
    req = client_metacustom.get('/sample')
    assert req.status == 200

    data = json_load(req.data)
    assert {'data', 'meta'} == set(data.keys())
    assert data['meta']['total_objects'] == 1
    assert data['meta']['total_pages'] == 1
    assert data['meta']['page'] == 1
    assert data['meta']['page_prev'] is None
    assert data['meta']['page_next'] is None
