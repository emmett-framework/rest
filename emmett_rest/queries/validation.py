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

from emmett.orm import geo

_geo_helpers = {
    'POINT': geo.Point,
    'LINE': geo.Line,
    'LINESTRING': geo.Line,
    'POLYGON': geo.Polygon
}
validate_default = lambda v: v


def _tuplify_list(v: List[Any]):
    rv = []
    for el in v:
        if isinstance(el, list):
            el = _tuplify_list(el)
        rv.append(el)
    return tuple(rv)


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


def validate_geo(v: Any) -> Any:
    assert isinstance(v, dict) and set(v.keys()) == {'type', 'coordinates'}
    objkey = v['type']
    geohelper = _geo_helpers.get(objkey.upper())
    assert geohelper and isinstance(v['coordinates'], list)
    try:
        return geohelper(*_tuplify_list(v['coordinates']))
    except Exception:
        raise AssertionError


def validate_geo_dwithin(v: Any) -> Any:
    assert isinstance(v, dict) and set(v.keys()) == {'geometry', 'distance'}
    assert v['distance']
    obj = validate_geo(v['geometry'])
    return (obj, v['distance'])


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
    '$le': op_validation_generator(int, float, datetime),
    '$ge': op_validation_generator(int, float, datetime),
    '$lte': op_validation_generator(int, float, datetime),
    '$gte': op_validation_generator(int, float, datetime),
    '$exists': op_validation_generator(bool),
    '$like': validate_default,
    '$ilike': validate_default,
    '$regex': validate_default,
    '$iregex': validate_default,
    '$geo.contains': validate_geo,
    '$geo.equals': validate_geo,
    '$geo.intersects': validate_geo,
    '$geo.overlaps': validate_geo,
    '$geo.touches': validate_geo,
    '$geo.within': validate_geo,
    '$geo.dwithin': validate_geo_dwithin
}
