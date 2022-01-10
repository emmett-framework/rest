# -*- coding: utf-8 -*-

import os
import pytest

from emmett import App, sdict
from emmett.asgi.loops import loops
from emmett.orm import Database
from emmett.orm.migrations.utils import generate_runtime_migration
from emmett.parsers import Parsers
from emmett.serializers import Serializers
from emmett_rest import REST


@pytest.fixture(scope='session')
def json_dump():
    return Serializers.get_for('json')


@pytest.fixture(scope='session')
def json_load():
    return Parsers.get_for('json')


@pytest.fixture(scope='session')
def event_loop():
    loop = loops.get('auto')
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def db_config():
    config = sdict()
    config.adapter = 'postgres:psycopg2'
    config.host = os.environ.get('POSTGRES_HOST', 'localhost')
    config.port = int(os.environ.get('POSTGRES_PORT', 5432))
    config.user = os.environ.get('POSTGRES_USER', 'postgres')
    config.password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
    config.database = os.environ.get('POSTGRES_DB', 'test')
    return config


@pytest.fixture(scope='session')
def app(event_loop, db_config):
    rv = App(__name__)
    rv.config.db = db_config
    rv.config.REST.use_save = False
    rv.config.REST.use_destroy = False
    rv.use_extension(REST)
    return rv


def _db_teardown_generator(db, migration):
    def teardown():
        with db.connection():
            migration.down()
    return teardown


@pytest.fixture(scope='function')
def raw_db(request, app):
    rv = Database(app)
    return rv


@pytest.fixture(scope='function')
def migration_db(request, app):
    def generator(*models):
        rv = Database(app)
        rv.define_models(*models)
        migration = generate_runtime_migration(rv)
        with rv.connection():
            migration.up()
        request.addfinalizer(_db_teardown_generator(rv, migration))
        return rv
    return generator
