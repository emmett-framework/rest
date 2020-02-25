# -*- coding: utf-8 -*-

import pytest

from pydal.objects import Query
from emmett import sdict, current, now
from emmett.orm import Field, Model
from emmett_rest.queries import JSONQueryPipe
from emmett_rest.queries.parser import parse_conditions


class Sample(Model):
    str = Field()
    int = Field.int()
    float = Field.float()
    datetime = Field.datetime()


@pytest.fixture(scope='function')
def db(raw_db):
    raw_db.define_models(Sample)
    return raw_db


def query_component_equal(c1, c2):
    qinst = [isinstance(el, Query) for el in [c1, c2]]
    if all(qinst):
        return queries_equal(c1, c2)
    if any(qinst):
        return False
    if isinstance(c1, Field):
        c1 = str(c1)
    if isinstance(c2, Field):
        c2 = str(c2)
    return c1 == c2


def queries_equal(q1, q2):
    ctx = [
        {'op': q1.op, 'elements': [q1.first, q1.second]},
        {'op': q2.op, 'elements': [q2.first, q2.second]}
    ]
    if ctx[0]['op'] != ctx[1]['op']:
        return False
    equality_count = 0
    for element1 in ctx[0]['elements']:
        for element2 in ctx[1]['elements']:
            if query_component_equal(element1, element2):
                equality_count += 1
    return equality_count == 2


def test_parse_fields(db):
    qdict = {
        'str': 'bar'
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'str'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: m.str == 'bar').query
    )

    qdict = {
        'str': {'$regex': 'bar'}
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'str'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(
            lambda m: m.str.contains('bar', case_sensitive=True)
        ).query
    )

    qdict = {
        'str': {'$iregex': 'bar'}
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'str'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: m.str.contains('bar')).query
    )

    qdict = {
        'int': 2
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'int'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: m.int == 2).query
    )

    qdict = {
        'int': {'$gte': 0, '$lt': 2}
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'int'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: (m.int >= 0) & (m.int < 2)).query
    )

    qdict = {
        'float': 2.3
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'float'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: m.float == 2.3).query
    )

    qdict = {
        'float': {'$gte': 2, '$lt': 5.5}
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'float'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: (m.float >= 2) & (m.float < 5.5)).query
    )

    dt1, dt2 = now(), now().add(days=1)
    qdict = {
        'datetime': dt1
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'datetime'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(lambda m: m.datetime == dt1).query
    )

    qdict = {
        'datetime': {'$gte': dt1, '$lt': dt2}
    }
    parsed = parse_conditions(Sample, Sample.all(), qdict, {'datetime'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(
            lambda m: (m.datetime >= dt1) & (m.datetime < dt2)
        ).query
    )


def test_parse_combined(db):
    dt1, dt2 = now(), now().add(days=1)
    qdict = {
        'str': 'bar',
        'int': {'$gt': 2},
        '$not': {'int': {'$in': [4, 5]}},
        '$or': [
            {'float': 3.2},
            {'datetime': {'$gte': dt1, '$lt': dt2}}
        ]
    }
    parsed = parse_conditions(
        Sample, Sample.all(), qdict, {'str', 'int', 'float', 'datetime'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(
            lambda m:
                (m.str == 'bar') &
                (m.int > 2) & (
                    ~m.int.belongs([4, 5]) & (
                        (m.float == 3.2) | (
                            (m.datetime >= dt1) & (m.datetime < dt2)
                        )
                    )
                )
        ).query
    )

    qdict = {
        '$or': [
            {'float': 3.2},
            {'datetime': {'$gte': dt1, '$lt': dt2}}
        ]
    }
    parsed = parse_conditions(
        Sample, Sample.all(), qdict, {'str', 'int', 'float', 'datetime'})
    assert queries_equal(
        parsed.query,
        Sample.all().where(
            lambda m:
                (m.float == 3.2) | (
                    (m.datetime >= dt1) & (m.datetime < dt2)
                )
        ).query
    )


async def _fake_pipe(**kwargs):
    return kwargs


@pytest.mark.asyncio
async def test_pipes(db, json_dump):
    fake_mod = sdict(
        _queryable_fields=['str', 'int'],
        model=Sample,
        ext=sdict(
            config=sdict(
                query_param='where'
            )
        )
    )
    pipe = JSONQueryPipe(fake_mod)

    qdict = {
        '$or': [
            {'str': 'bar'},
            {'int': {'$gt': 0}}
        ]
    }
    current.request = sdict(
        query_params=sdict(
            where=json_dump(qdict)))
    res = await pipe.pipe(_fake_pipe)
    assert queries_equal(
        res['dbset'].query,
        Sample.all().where(lambda m: (m.str == 'bar') | (m.int > 0)).query
    )
