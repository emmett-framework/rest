# -*- coding: utf-8 -*-
"""
    emmett_rest.queries.validation
    ------------------------------

    Provides REST query language validation

    :copyright: 2017 Giovanni Barillari
    :license: BSD-3-Clause
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List

validate_default = lambda v: v


def op_validation_generator(*types) -> Callable[[Any], Any]:
    def op_validator(v: Any) -> Any:
        assert isinstance(v, types)
        return v
    return op_validator


def validate_glue(v: Any) -> List[Dict[str, Any]]:
    assert isinstance(v, list)
    for element in v:
        assert isinstance(element, dict)
    return v


op_validators = {
    '$and': validate_glue,
    '$or': validate_glue,
    '$eq': validate_default,
    '$not': op_validation_generator(dict),
    '$ne': validate_default,
    '$in': op_validation_generator(list),
    '$nin': op_validation_generator(list),
    '$lt': op_validation_generator(int, float, datetime),
    '$gt': op_validation_generator(int, float, datetime),
    '$lte': op_validation_generator(int, float, datetime),
    '$gte': op_validation_generator(int, float, datetime),
    '$exists': op_validation_generator(bool),
    '$regex': validate_default,
    '$iregex': validate_default
}
