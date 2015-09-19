Is Your REST API RESTful?
=========================

[![Build Status](https://travis-ci.org/miguelgrinberg/api-pycon2015.png?branch=master)](https://travis-ci.org/miguelgrinberg/api-pycon2015)

This repository contains a fully working API project that implements the techniques that I discussed in my [PyCon 2015 talk](https://us.pycon.org/2015/schedule/presentation/355/) on building REST APIs.

The API in this example implements a "students and classes" system and demonstrates RESTful principles, CRUD operations, error handling, user authentication, filtering, sorting and pagination of collections, rate limiting and HTTP caching.

Requirements
------------

To install and run this application you need:

- Python 3.4 (2.7 works too)
- Redis (optional, for the rate limiting feature)

Installation
------------

The commands below install the application and its dependencies:

    $ git clone https://github.com/miguelgrinberg/api-pycon2015.git
    $ cd api-pycon2015
    $ python3.4 -m venv venv
    $ source venv/bin/activate
    (venv) pip install -r requirements.txt

The core dependencies are Flask, Flask-HTTPAuth, Flask-SQLAlchemy, Flask-Script and redis. For unit tests nose and coverage are used. The httpie command line HTTP client is also installed as a convenience.

Unit Tests
----------

To ensure that your installation was successful you can run the unit tests:

    (venv) $ python manage.py test
    test_bad_auth (tests.test_api.TestAPI) ... ok
    test_classes (tests.test_api.TestAPI) ... ok
    test_etag (tests.test_api.TestAPI) ... ok
    test_expanded_collections (tests.test_api.TestAPI) ... ok
    test_filters (tests.test_api.TestAPI) ... ok
    test_pagination (tests.test_api.TestAPI) ... ok
    test_password_auth (tests.test_api.TestAPI) ... ok
    test_rate_limits (tests.test_api.TestAPI) ... ok
    test_registrations (tests.test_api.TestAPI) ... ok
    test_sorting (tests.test_api.TestAPI) ... ok
    test_students (tests.test_api.TestAPI) ... ok
    test_user_password_not_readable (tests.test_api.TestAPI) ... ok

    Name                   Stmts   Miss Branch BrMiss  Cover   Missing
    ------------------------------------------------------------------
    api                        0      0      0      0   100%
    api.app                   26      2      5      1    90%   34, 38
    api.auth                  13      0      2      0   100%
    api.decorators           120     10     61      4    92%   19, 155-163, 167
    api.errors                41     13      6      3    66%   26, 36-39, 43-46, 50-52, 62-65
    api.helpers               22      6     11      6    64%   10, 17-19, 26, 33
    api.models                81      0      0      0   100%
    api.rate_limit            38      1      6      1    95%   39
    api.token                 18      6      2      2    60%   13-16, 21, 31
    api.v1                    20      1      2      0    95%   18
    api.v1.classes            47      0      0      0   100%
    api.v1.registrations      25      0      0      0   100%
    api.v1.students           47      0      0      0   100%
    ------------------------------------------------------------------
    TOTAL                    498     39     95     17    91%
    ----------------------------------------------------------------------
    Ran 12 tests in 1.583s

    OK

The report printed below the tests is a summary of the test coverage. A more detailed report is written to a `cover` folder. To view it, open `cover/index.html` with your web browser.

User Registration
-----------------

The API can only be accessed by authenticated users. New users can be registered with the application from the command line:

    (venv) $ python manage.py adduser <username>
    Password: <password>
    Confirm: <password>
    User <username> was registered successfully.

The system supports multiple users, so the above command can be issued as many times as needed with different usernames and passwords. Users are stored in the application's database, which by default uses the SQLite engine. An empty database is created in the current folder if a previous database file is not found.

Authentication
--------------

The default configuration uses tokens for authentication. When the client sends a request to the API without authenticating, a response with status code 401 is returned. The `Location` header in this response is set to the token request URL. To obtain a token, the client must send a `POST` request to this URL with valid username and password in a HTTP basic authentication header. The response to this request will include a token valid for one hour. After the token expires a new token must be requested.

To switch to a simper username and password authentication the configuration stored in `config.py` must be edited as follows:

    USE_TOKEN_AUTH = False 

After this change restart the application for the change to take effect. When username and password authentication is used, all request must include the credentials in a HTTP basic authentication header.

API Documentation
-----------------

General notes about this API:

- All resource representations are in JSON format.

The API supported by this application contains three top-level resource collections:

- *students*: The collection of students.
- *classes*: The collection of classes.
- *registrations*: The collection of student-to-class registrations.

To obtain the URLs of these resources clients must send a request to the root URL of the API to obtain the API version catalog:

    {
        "versions": {
            "v1": {
                "classes_url": "[class-collection-url]",
                "registrations_url": "[registration-collection-url]",
                "students_url": "[student-collection-url]"
            }
        }
    }

To see an example of how a client can use this information to access the API see the unit tests.

### Resource Collections

Resource collection URLs accept `GET` and `POST` requests. Use a `GET` request to retrieve the collection, and a `POST` request to insert a new item into the collection.

#### Filtering

Resource collections can be filtered by adding the `filter` argument to the query string of the collection resource URL. The format of a filter is as follows:

    [field_name],[operator],[value]

To build more complex queries multiple filters can be concatenated with a `;` separator. The operators can be `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `like` and `in`. The `in` operator takes a list of values separated by commas, while all other operators take a single value. Examples:

- Search by exact value: `filter=name,eq,john`
- Search by range (all names that begin with "a"): `filter=name,ge,a;name,lt,b`
- Search in a set: `filter=name,in,john,susan,mary`

Invalid filters are silently ignored.

#### Sorting

Collections can be sorted by adding the `sort` argument to the query string of the collection resource URL. The format of this argument is as follows:

    [field_name],[asc|desc]

To specify multiple sort orders contactenate them with a `;` separator. The sort order can be `asc` or `desc`. If not specified `asc` is used. Examples:

- Sort by name: `sort=name`
- Sort by name in descending order: `sort=name,desc`
- Sort by name in ascending order and then by id in descending order: `sort=name,asc;id,desc`

Invalid sort specifications are silently ignored.

#### Resource Expansion

By default, when a collection of resources is returned, only their URLs are returned, as this maximizes caching efficiency. Example:

    {
        "students": [
            "[student-resource-url-1]",
            "[student-resource-url-2]",
            "[student-resource-url-3]"
        ]
    }

However, in certain occasions it may be more convenient to obtain all the resources expanded. To request the resources in expanded form add `expand=1` to the query string of the collection resource URL. Example:

    {
        "students": [
            {
                "name": "john",
                "registrations_url": "[student-registration-url-1]",
                "self_url": "[student-resource-url-1]"
            },
            {
                "name": "susan",
                "registrations_url": "[student-registration-url-2]",
                "self_url": "[student-resource-url-2]"
            },
            {
                "name": "mary",
                "registrations_url": "[student-registration-url-3]",
                "self_url": "[student-resource-url-3]"
            }
        ]
    }

#### Pagination

All requests to resource collection URLs are paginated, regardless of the client requesting so or not. The response from the server includes a `'meta'` key with information that is useful to navigate the pages of resources. Example:

    {
        "meta": {
            "first_url": "[students-collection-url]?per_page=10&page=1",
            "last_url": "[students-collection-url]?per_page=10&page=4",
            "next_url": "[students-collection-url]?per_page=10&page=2",
            "page": 1,
            "pages": 4,
            "per_page": 10,
            "prev_url": null,
            "total": 37
        },
        "students": [
            ...
        ]
    }

The `first_url`, `last_url`, `next_url` and `prev_url` fields contain the URLs to request other pages of the collection. When filtering, sorting and embedding options are used, these URLs contain the same options that were given for the current request.

The `page`, `pages`, `total` and `per_page` provide the current page, total number of pages, total number of items and items per page values respectively.

To request pagination settings that are different than the default, the `per_page` and `page` query string arguments must be added to the collection request URL. The server is not obligated to honor the `per_page` size requested by the client.

### Student Resource

A student resource has the following structure:

    {
        "name": [student name],
        "registrations_url": [link to student registrations]
        "self_url": [student URL],
    }

The student resource supports `GET`, `POST`, `PUT` and `DELETE` methods to retrieve, create, edit and delete respectively. The `POST` and `PUT` requests only require the `name` field in the request body.

A `GET` request to the URL given in the `registrations_url` field returns the collection of class registrations for the student. A `POST` request to this URL including `class_url` in the body adds a registration to a class.

### Class Resource

The class resource has a similar structure:

    {
        "name": [class name],
        "registrations_url": [link to class registrations]
        "self_url": [class URL],
    }

The class resource supports `GET`, `POST`, `PUT` and `DELETE` methods to retrieve, create, edit and delete respectively. The `POST` and `PUT` requests only require the `name` field in the request body.

A `GET` request to the URL given in the `registrations_url` field returns the collection of registrations for the class. A `POST` request to this URL including `student_url` in the body adds the student to the class.

### Registration Resource

The registration resource associates a student with a class. Below is the structure of this resource:

    {
        "student_url": [student URL],
        "class_url": [class URL],
        "timestamp": [date of registration]
        "self_url": [registration URL],
    }

The registration resource supports `GET`, `POST` and `DELETE` methods, to retrieve, create and delete respectively.

HTTP Caching
------------

The different API endpoints are configured to respond using the appropriate caching directives. All the `GET` requests return an `ETag` header that HTTP caches can use with the `If-Match` and `If-None-Match` headers.

Rate Limiting
-------------

This API supports rate limiting as an optional feature. To use rate limiting the application must have access to a Redis server running on the same host and listening on the default port. If a redis server isn't available then rate limiting is automatically disabled.

The default configuration limits clients to 5 API calls per 15 second interval. When a client goes over the limit a response with the 429 status code is returned immediately, without carrying out the request. The limit resets as soon as the current 15 second period ends.

When rate limiting is enabled all responses return three additional headers:

    X-RateLimit-Limit: [period in seconds]
    X-RateLimit-Remaining: [remaining calls in this period]
    X-RateLimit-Reset: [time when the limits reset, in UTC epoch seconds]
