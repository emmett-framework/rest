# -*- coding: utf-8 -*-
"""
    emmett_rest.queries.parser
    --------------------------

    Provides REST query language parser

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

import operator

from emmett import sdict
from emmett.orm.objects import Expression, Query, Set as DBSet
from functools import reduce
from typing import Any, Callable, Dict, Optional, Set, Union

from ..typing import ModelType
from .errors import QueryError
from .validation import op_validators


_query_operators = {
    '$and': operator.and_,
    '$or': operator.or_,
    '$not': lambda field, value: operator.inv(value),
    '$eq': operator.eq,
    '$ne': operator.ne,
    '$lt': operator.lt,
    '$gt': operator.gt,
    '$le': operator.le,
    '$ge': operator.ge,
    '$lte': operator.le,
    '$gte': operator.ge,
    '$in': lambda field, value: operator.methodcaller('belongs', value)(field),
    '$exists': lambda field, value: (
        operator.ne(field, None) if value else operator.eq(field, None)
    ),
    '$contains': lambda field, value: (
        operator.methodcaller('contains', value, case_sensitive=True)(field)
    ),
    '$icontains': lambda field, value: (
        operator.methodcaller('contains', value, case_sensitive=False)(field)
    ),
    '$like': lambda field, value: (
        operator.methodcaller('like', value, case_sensitive=True)(field)
    ),
    '$ilike': lambda field, value: (
        operator.methodcaller('like', value, case_sensitive=False)(field)
    ),
    '$regex': lambda field, value: (
        operator.methodcaller('contains', value, case_sensitive=True)(field)
    ),
    '$iregex': lambda field, value: (
        operator.methodcaller('contains', value, case_sensitive=False)(field)
    ),
    '$geo.contains': lambda field, value: (
        operator.methodcaller('st_contains', value)(field)
    ),
    '$geo.equals': lambda field, value: (
        operator.methodcaller('st_equals', value)(field)
    ),
    '$geo.intersects': lambda field, value: (
        operator.methodcaller('st_intersects', value)(field)
    ),
    '$geo.overlaps': lambda field, value: (
        operator.methodcaller('st_overlaps', value)(field)
    ),
    '$geo.touches': lambda field, value: (
        operator.methodcaller('st_touches', value)(field)
    ),
    '$geo.within': lambda field, value: (
        operator.methodcaller('st_within', value)(field)
    ),
    '$geo.dwithin': lambda field, value: (
        operator.methodcaller('st_dwithin', value[0], value[1])(field)
    )
}


def _glue_op_parser(key: str, value: Any, ctx: sdict) -> Expression:
    if not isinstance(value, list):
        raise QueryError(op=key, value=value)
    op = _query_operators[key]
    return reduce(
        lambda a, b: op(a, b) if a and b else None, map(
            lambda v: _conditions_parser(
                ctx.op_set, ctx.op_validators, ctx.op_parsers,
                ctx.model, v, ctx.accepted_set,
                parent=key
            ), value
        )
    )


def _dict_op_parser(key: str, value: Any, ctx: sdict) -> Expression:
    if not isinstance(value, dict):
        raise QueryError(op=key, value=value)
    op = _query_operators[key]
    inner = _conditions_parser(
        ctx.op_set, ctx.op_validators, ctx.op_parsers,
        ctx.model, value, ctx.accepted_set,
        parent=key
    )
    return op(None, inner)


def _generic_op_parser(key: str, value: Any, ctx: sdict) -> Expression:
    op_validator = ctx.op_validators[key]
    try:
        value = op_validator(value)
        op, field = _query_operators[key], ctx.model.table[ctx.parent]
        value = op(field, value)
    except AssertionError:
        raise QueryError(op=key, value=value)
    return value


op_parsers = {key: _generic_op_parser for key in op_validators.keys()}
op_parsers.update({
    '$or': _glue_op_parser,
    '$and': _glue_op_parser,
    '$not': _dict_op_parser
})


def _conditions_parser(
    op_set: Set[str],
    op_validators: Dict[str, Callable[[Any], Any]],
    op_parsers: Dict[str, Callable[[str, Any, sdict], Any]],
    model: ModelType,
    query_dict: Dict[str, Any],
    accepted_set: Set[str],
    parent: Optional[str] = None
) -> Union[Query, None]:
    query, ctx = None, sdict(
        op_set=op_set,
        op_validators=op_validators,
        op_parsers=op_parsers,
        model=model,
        accepted_set=accepted_set,
        parent=parent
    )
    query_key_set = set(query_dict.keys())
    step_conditions, inner_conditions = [], []
    for key in query_key_set & op_set:
        step_conditions.append(op_parsers[key](key, query_dict[key], ctx))
    if step_conditions:
        step_query = reduce(
            lambda a, b: operator.and_(a, b) if a and b else None,
            step_conditions
        )
        query = query & step_query if query else step_query
    for key in accepted_set & query_key_set:
        value = query_dict[key]
        if not isinstance(value, dict):
            value = {'$eq': value}
        inner_conditions.append(
            _conditions_parser(
                op_set, op_validators, op_parsers,
                model,
                value, accepted_set, parent=key
            )
        )
    if inner_conditions:
        inner_query = reduce(
            lambda a, b: operator.and_(a, b) if a and b else None,
            inner_conditions
        )
        query = query & inner_query if query else inner_query
    return query


def _build_scoped_conditions_parser(
    op_validators: Dict[str, Callable[[Any], Any]],
    op_parsers: Dict[str, Callable[[str, Any, sdict], Any]]
) -> Callable[[ModelType, DBSet, Dict[str, Any], Set[str]], DBSet]:
    op_set = set(op_validators.keys())

    def scoped(
        model: ModelType,
        dbset: DBSet,
        query_dict: Dict[str, Any],
        accepted_set: Set[str]
    ) -> DBSet:
        return dbset.where(
            _conditions_parser(
                op_set, op_validators, op_parsers,
                model, query_dict, accepted_set
            )
        )
    return scoped


parse_conditions = _build_scoped_conditions_parser(op_validators, op_parsers)
