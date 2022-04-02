## API Reference

The {{ =title }} is organized around REST. Our API has predictable resource-oriented URLs, accepts JSON-encoded or form-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes, authentication, and verbs.

## Pagination

All top-level API resources have support for bulk fetches via "list" API methods. These list API methods share a common structure, taking at least these three query parameters: `page`, `page_size`, and `sort_by`.

## Filtering

API resources implementing "list" methods might have support for filtering. These list API methods share a common behaviour and filtering language, using the `where` query parameter. The value for such parameter should be a JSON encoded object containing queries following the language specifications.

#### Filtering Language

{{
    operators = [
        ("$eq", "any", "matches values equal to argument"),
        ("$ne", "any", "matches values not equal to argument"),
        ("$and", "list[mapping[any]]", "logical AND"),
        ("$or", "list[mapping[any]]", "logical OR"),
        ("$not", "mapping[any]", "invert argument"),
        ("$in", "list[any]", "matches values equal to any argument element"),
        ("$nin", "list[any]", "matches values not equal to argument elements"),
        ("$lt", "any", "matches values less than argument"),
        ("$gt", "any", "matches values greater than argument"),
        ("$lte", "any", "matches values less or equal than argument"),
        ("$gte", "any", "matches values greater or equal than argument"),
        ("$exists", "boolean", "matches not null or null values"),
        ("$contains", "string", "text search (case sensitive)"),
        ("$icontains", "string", "text search (case insensitive)"),
        ("$like", "string", "like match (case sensitive)"),
        ("$ilike", "string", "like match (case insensitive)"),
        ("$geo.contains", "GeoJSON", "GIS ST_Contains"),
        ("$geo.equals", "GeoJSON", "GIS ST_Equals"),
        ("$geo.intersects", "GeoJSON", "GIS ST_Intersects"),
        ("$geo.overlaps", "GeoJSON", "GIS ST_Overlaps"),
        ("$geo.touches", "GeoJSON", "GIS ST_Touches"),
        ("$geo.within", "GeoJSON", "GIS ST_Within"),
        ("$geo.dwithin", "GeoDistance", "GIS ST_DWithin")
    ]
}}

The filtering language provides the following operators:

| operator | argument type | description |
| --- | --- | --- |
{{ for op_name, op_arg, op_desc in operators: }}
| `{{ =op_name }}` | *{{ =op_arg }}* | {{ =op_desc }} |
{{ pass }}

The final condition condition should always have fields' names as keys (except for `$and`, `$or`, `$not`) and operators as values, where `$eq` is the default one.
