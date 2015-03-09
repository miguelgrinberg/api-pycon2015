import functools
import hashlib
from flask import jsonify, request, url_for, current_app, make_response, g
from .rate_limit import RateLimit
from .errors import too_many_requests, precondition_failed, not_modified, ValidationError


def json(f):
    """This decorator generates a JSON response from a Python dictionary or
    a SQLAlchemy model."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        rv = f(*args, **kwargs)
        status_or_headers = None
        headers = None
        if isinstance(rv, tuple):
            rv, status_or_headers, headers = rv + (None,) * (3 - len(rv))
        if isinstance(status_or_headers, (dict, list)):
            headers, status_or_headers = status_or_headers, None
        if not isinstance(rv, dict):
            # assume it is a model, call its export_data() method
            rv = rv.export_data()

        rv = jsonify(rv)
        if status_or_headers is not None:
            rv.status_code = status_or_headers
        if headers is not None:
            rv.headers.extend(headers)
        return rv
    return wrapped


def rate_limit(limit, period):
    """This decorator implements rate limiting."""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            if current_app.config['USE_RATE_LIMITS']:
                # generate a unique key to represent the decorated function and
                # the IP address of the client. Rate limiting counters are
                # maintained on each unique key.
                key = '{0}/{1}'.format(f.__name__, str(g.user.id))
                limiter = RateLimit(key, limit, period)

                # set the rate limit headers in g, so that they are picked up
                # by the after_request handler and attached to the response
                g.headers = {
                    'X-RateLimit-Remaining': str(limiter.remaining
                        if limiter.remaining >= 0 else 0),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Reset': str(limiter.reset)
                }

                # if the client went over the limit respond with a 429 status
                # code, else invoke the wrapped function
                if not limiter.allowed:
                    return too_many_requests()

            # let the request through
            return f(*args, **kwargs)
        return wrapped
    return decorator


def _filter_query(model, query, filter_spec):
    filters = [f.split(',') for f in filter_spec.split(';')]
    for f in filters:
        if len(f) < 3 or (len(f) > 3 and f[1] != 'in'):
            continue
        if f[1] == 'in':
            f = [f[0], f[1], f[2:]]
        ops = {'eq': '__eq__', 'ne': '__ne__', 'lt': '__lt__', 'le': '__le__',
               'gt': '__gt__', 'ge': '__ge__', 'in': 'in_', 'like': 'like'}
        if hasattr(model, f[0]) and f[1] in ops.keys():
            column = getattr(model, f[0])
            op = ops[f[1]]
            query = query.filter(getattr(column, op)(f[2]))
    return query


def _sort_query(model, query, sort_spec):
    sort = [s.split(',') for s in sort_spec.split(';')]
    for s in sort:
        if hasattr(model, s[0]):
            column = getattr(model, s[0])
            if len(s) == 2 and s[1] in ['asc', 'desc']:
                query = query.order_by(getattr(column, s[1])())
            else:
                query = query.order_by(column.asc())
    return query


def collection(model, name=None, max_per_page=10):
    """This decorator implements pagination, filtering, sorting and expanding
    for collections. The expected response from the decorated route is a
    SQLAlchemy query."""
    if name is None:
        name = model.__tablename__

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            query = f(*args, **kwargs)

            # filtering and sorting
            filter = request.args.get('filter')
            if filter:
                query = _filter_query(model, query, filter)
            sort = request.args.get('sort')
            if sort:
                query = _sort_query(model, query, sort)

            # pagination
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', max_per_page,
                                            type=int), max_per_page)
            expand = request.args.get('expand')

            p = query.paginate(page, per_page)
            pages = {'page': page, 'per_page': per_page,
                     'total': p.total, 'pages': p.pages}
            if p.has_prev:
                pages['prev_url'] = url_for(request.endpoint, page=p.prev_num,
                                            per_page=per_page,
                                            expand=expand, _external=True,
                                            **kwargs)
            else:
                pages['prev_url'] = None
            if p.has_next:
                pages['next_url'] = url_for(request.endpoint, filter=filter,
                                            sort=sort, page=p.next_num,
                                            per_page=per_page,
                                            expand=expand, _external=True,
                                            **kwargs)
            else:
                pages['next_url'] = None
            pages['first_url'] = url_for(request.endpoint, filter=filter,
                                         sort=sort, page=1, per_page=per_page,
                                         expand=expand, _external=True,
                                         **kwargs)
            pages['last_url'] = url_for(request.endpoint, filter=filter,
                                        sort=sort, page=p.pages,
                                        per_page=per_page, expand=expand,
                                        _external=True, **kwargs)
            if expand:
                items = [item.export_data() for item in p.items]
            else:
                items = [item.get_url() for item in p.items]
            return {name: items, 'meta': pages}
        return wrapped
    return decorator


def etag(f):
    """This decorator adds an ETag header to the response."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        # only for HEAD and GET requests
        assert request.method in ['HEAD', 'GET'],\
            '@etag is only supported for GET requests'
        rv = f(*args, **kwargs)
        rv = make_response(rv)
        etag = '"' + hashlib.md5(rv.get_data()).hexdigest() + '"'
        rv.headers['Cache-Control'] = 'max-age=86400'
        rv.headers['ETag'] = etag
        if_match = request.headers.get('If-Match')
        if_none_match = request.headers.get('If-None-Match')
        if if_match:
            etag_list = [tag.strip() for tag in if_match.split(',')]
            if etag not in etag_list and '*' not in etag_list:
                rv = precondition_failed()
        elif if_none_match:
            etag_list = [tag.strip() for tag in if_none_match.split(',')]
            if etag in etag_list or '*' in etag_list:
                rv = not_modified()
        return rv
    return wrapped
