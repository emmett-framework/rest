# -*- coding: utf-8 -*-

import os
import pytest

from emmett import App, sdict
from emmett.asgi.loops import loops
from emmett.orm import Database
from emmett.orm.migrations.generation import Generator
from emmett.orm.migrations.operations import MigrationOp
from emmett.serializers import Serializers


class DynamicGenerator(Generator):
    def _load_head_to_meta(self):
        pass


@pytest.fixture(scope='session')
def json_dump():
    return Serializers.get_for('json')


@pytest.yield_fixture(scope='session')
def event_loop():
    loop = loops.get_loop('auto')
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def db_config():
    config = sdict()
    config.adapter = 'postgres:psycopg2'
    config.host = os.environ.get('POSTGRES_HOST', 'localhost')
    config.user = os.environ.get('POSTGRES_USER', 'postgres')
    config.password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
    config.database = os.environ.get('POSTGRES_DB', 'test')
    return config


@pytest.fixture(scope='session')
def app(event_loop, db_config):
    rv = App(__name__)
    rv.config.db = db_config
    return rv


def _db_up(db):
    upgrade_ops = DynamicGenerator.generate_from(db, None, None)
    migration = MigrationOp('test', upgrade_ops, upgrade_ops.reverse(), 'test')
    migration.engine = db
    with db.connection():
        for op in migration.upgrade_ops:
            op.run()
    return migration


def _db_teardown_generator(db, migration):
    def teardown():
        with db.connection():
            for op in migration.downgrade_ops:
                op.run()
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
        migration = _db_up(rv)
        request.addfinalizer(_db_teardown_generator(rv, migration))
        return rv
    return generator
