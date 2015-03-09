import unittest
from werkzeug.exceptions import BadRequest
from .test_client import TestClient
from api.app import create_app
from api.models import db, User
from api.errors import ValidationError


class TestAPI(unittest.TestCase):
    default_username = 'dave'
    default_password = 'cat'

    def setUp(self):
        self.app = create_app('test_config')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        u = User(username=self.default_username,
                 password=self.default_password)
        db.session.add(u)
        db.session.commit()
        self.client = TestClient(self.app, u.generate_auth_token(), '')
        self.catalog = self._get_catalog()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _get_catalog(self, version='v1'):
        rv, json = self.client.get('/')
        return json['versions'][version]

    def test_password_auth(self):
        self.app.config['USE_TOKEN_AUTH'] = False
        good_client = TestClient(self.app, self.default_username,
                                 self.default_password)
        rv, json = good_client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)

        self.app.config['USE_TOKEN_AUTH'] = True
        u = User.query.get(1)
        good_client = TestClient(self.app, u.generate_auth_token(), '')
        rv, json = good_client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)

    def test_bad_auth(self):
        self.app.config['USE_TOKEN_AUTH'] = False
        bad_client = TestClient(self.app, 'abc', 'def')
        rv, json = bad_client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 401)

        self.app.config['USE_TOKEN_AUTH'] = True
        bad_client = TestClient(self.app, 'bad_token', '')
        rv, json = bad_client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 401)

    def test_token(self):
        self.app.config['USE_TOKEN_AUTH'] = True
        client = TestClient(self.app, self.default_username,
                            self.default_password)
        rv, json = client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 401)

        rv, json = client.post(rv.headers['Location'], data={})
        self.assertTrue(rv.status_code == 200)
        token = json['token']

        client = TestClient(self.app, token, '')
        rv, json = client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)

    def test_user_password_not_readable(self):
        u = User(username='john', password='cat')
        self.assertRaises(AttributeError, lambda: u.password)

    def test_http_errors(self):
        # not found
        rv, json = self.client.get('/a-bad-url')
        self.assertTrue(rv.status_code == 404)

        # method not allowed
        rv, json = self.client.delete(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 405)

    def test_students(self):
        # get collection
        rv, json = self.client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [])

        # create new
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'susan'})
        self.assertTrue(rv.status_code == 201)
        susan_url = rv.headers['Location']

        # get
        rv, json = self.client.get(susan_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'susan')
        self.assertTrue(json['self_url'] == susan_url)

        # create new
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'david'})
        self.assertTrue(rv.status_code == 201)
        david_url = rv.headers['Location']

        # get
        rv, json = self.client.get(david_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'david')
        self.assertTrue(json['self_url'] == david_url)

        # bad request
        rv,json = self.client.post(self.catalog['students_url'], data=None)
        self.assertTrue(rv.status_code == 400)
        rv,json = self.client.post(self.catalog['students_url'], data={})
        self.assertTrue(rv.status_code == 400)
        self.assertRaises(ValidationError,
                          lambda: self.client.post(self.catalog['students_url'],
                                                   data={'foo': 'david'}))

        # modify
        rv, json = self.client.put(david_url, data={'name': 'david2'})
        self.assertTrue(rv.status_code == 200)

        # get
        rv, json = self.client.get(david_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'david2')

        # get collection
        rv, json = self.client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(susan_url in json['students'])
        self.assertTrue(david_url in json['students'])
        self.assertTrue(len(json['students']) == 2)

        # delete
        rv, json = self.client.delete(susan_url)
        self.assertTrue(rv.status_code == 200)

        # get collection
        rv, json = self.client.get(self.catalog['students_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertFalse(susan_url in json['students'])
        self.assertTrue(david_url in json['students'])
        self.assertTrue(len(json['students']) == 1)

    def test_classes(self):
        # get collection
        rv, json = self.client.get(self.catalog['classes_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['classes'] == [])

        # create new
        rv, json = self.client.post(self.catalog['classes_url'],
                                    data={'name': 'algebra'})
        self.assertTrue(rv.status_code == 201)
        algebra_url = rv.headers['Location']

        # get
        rv, json = self.client.get(algebra_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'algebra')
        self.assertTrue(json['self_url'] == algebra_url)

        # create new
        rv, json = self.client.post(self.catalog['classes_url'],
                                    data={'name': 'lit'})
        self.assertTrue(rv.status_code == 201)
        lit_url = rv.headers['Location']

        # get
        rv, json = self.client.get(lit_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'lit')
        self.assertTrue(json['self_url'] == lit_url)

        # bad request
        rv,json = self.client.post(self.catalog['classes_url'], data=None)
        self.assertTrue(rv.status_code == 400)
        rv,json = self.client.post(self.catalog['classes_url'], data={})
        self.assertTrue(rv.status_code == 400)
        self.assertRaises(ValidationError,
                          lambda: self.client.post(self.catalog['classes_url'],
                                                   data={'foo': 'lit'}))

        # modify
        rv, json = self.client.put(lit_url, data={'name': 'lit2'})
        self.assertTrue(rv.status_code == 200)

        # get
        rv, json = self.client.get(lit_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['name'] == 'lit2')

        # get collection
        rv, json = self.client.get(self.catalog['classes_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(algebra_url in json['classes'])
        self.assertTrue(lit_url in json['classes'])
        self.assertTrue(len(json['classes']) == 2)

        # delete
        rv, json = self.client.delete(lit_url)
        self.assertTrue(rv.status_code == 200)

        # get collection
        rv, json = self.client.get(self.catalog['classes_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(algebra_url in json['classes'])
        self.assertFalse(lit_url in json['classes'])
        self.assertTrue(len(json['classes']) == 1)

    def test_registrations(self):
        # create new students
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'susan'})
        self.assertTrue(rv.status_code == 201)
        susan_url = rv.headers['Location']

        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'david'})
        self.assertTrue(rv.status_code == 201)
        david_url = rv.headers['Location']

        # create new classes
        rv, json = self.client.post(self.catalog['classes_url'],
                                    data={'name': 'algebra'})
        self.assertTrue(rv.status_code == 201)
        algebra_url = rv.headers['Location']

        rv, json = self.client.post(self.catalog['classes_url'],
                                    data={'name': 'lit'})
        self.assertTrue(rv.status_code == 201)
        lit_url = rv.headers['Location']

        # register students to classes
        rv, json = self.client.post(self.catalog['registrations_url'],
                                    data={'student_url': susan_url,
                                          'class_url': algebra_url})
        self.assertTrue(rv.status_code == 201)
        susan_in_algebra_url = rv.headers['Location']

        rv, json = self.client.post(self.catalog['registrations_url'],
                                    data={'student_url': susan_url,
                                          'class_url': lit_url})
        self.assertTrue(rv.status_code == 201)
        susan_in_lit_url = rv.headers['Location']

        rv, json = self.client.post(self.catalog['registrations_url'],
                                    data={'student_url': david_url,
                                          'class_url': algebra_url})
        self.assertTrue(rv.status_code == 201)
        david_in_algebra_url = rv.headers['Location']

        # get registration
        rv, json = self.client.get(susan_in_lit_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['student_url'] == susan_url)
        self.assertTrue(json['class_url'] == lit_url)

        # get collection
        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(susan_in_algebra_url in json['registrations'])
        self.assertTrue(susan_in_lit_url in json['registrations'])
        self.assertTrue(david_in_algebra_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 3)

        # bad registrations
        rv,json = self.client.post(self.catalog['registrations_url'],
                                   data=None)
        self.assertTrue(rv.status_code == 400)
        rv,json = self.client.post(self.catalog['registrations_url'], data={})
        self.assertTrue(rv.status_code == 400)

        # missing class URL
        self.assertRaises(ValidationError,
                          lambda: self.client.post(
                              self.catalog['registrations_url'],
                              data={'student_url': david_url}))

        # missing student URL
        self.assertRaises(ValidationError,
                          lambda: self.client.post(
                              self.catalog['registrations_url'],
                              data={'class_url': algebra_url}))

        # class is not a URL
        self.assertRaises(ValidationError,
                          lambda: self.client.post(
                              self.catalog['registrations_url'],
                              data={'student_url': david_url,
                                    'class_url': 'foo'}))

        # class is a not found URL
        self.assertRaises(ValidationError,
                          lambda: self.client.post(
                              self.catalog['registrations_url'],
                              data={'student_url': david_url,
                                    'class_url': algebra_url + '1'}))

        # class is an invalid URL
        self.assertRaises(ValidationError,
                          lambda: self.client.post(
                              self.catalog['registrations_url'],
                              data={'student_url': david_url,
                                    'class_url': david_url}))
        db.session.remove()

        # get classes from each student
        rv, json = self.client.get(susan_url)
        self.assertTrue(rv.status_code == 200)
        susans_reg_url = json['registrations_url']
        rv, json = self.client.get(susans_reg_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(susan_in_algebra_url in json['registrations'])
        self.assertTrue(susan_in_lit_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 2)

        rv, json = self.client.get(david_url)
        self.assertTrue(rv.status_code == 200)
        davids_reg_url = json['registrations_url']
        rv, json = self.client.get(davids_reg_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(david_in_algebra_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 1)

        # get students for each class
        rv, json = self.client.get(algebra_url)
        self.assertTrue(rv.status_code == 200)
        algebras_reg_url = json['registrations_url']
        rv, json = self.client.get(algebras_reg_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(susan_in_algebra_url in json['registrations'])
        self.assertTrue(david_in_algebra_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 2)

        rv, json = self.client.get(lit_url)
        self.assertTrue(rv.status_code == 200)
        lits_reg_url = json['registrations_url']
        rv, json = self.client.get(lits_reg_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(susan_in_lit_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 1)

        # unregister students
        rv, json = self.client.delete(susan_in_algebra_url)
        self.assertTrue(rv.status_code == 200)

        rv, json = self.client.delete(david_in_algebra_url)
        self.assertTrue(rv.status_code == 200)

        # get collection
        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertFalse(susan_in_algebra_url in json['registrations'])
        self.assertTrue(susan_in_lit_url in json['registrations'])
        self.assertFalse(david_in_algebra_url in json['registrations'])
        self.assertTrue(len(json['registrations']) == 1)

        # delete student
        rv, json = self.client.delete(susan_url)
        self.assertTrue(rv.status_code == 200)

        # get collection
        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['registrations']) == 0)

        # register through student registrations URL
        rv, json = self.client.get(david_url)
        rv, json = self.client.post(json['registrations_url'],
                                    data={'class_url': lit_url})
        self.assertTrue(rv.status_code == 201)

        # register through class registrations URL
        rv, json = self.client.get(algebra_url)
        rv, json = self.client.post(json['registrations_url'],
                                    data={'student_url': david_url})
        self.assertTrue(rv.status_code == 201)

        # get collection
        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['registrations']) == 2)

    def test_rate_limits(self):
        self.app.config['USE_RATE_LIMITS'] = True

        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        self.assertTrue('X-RateLimit-Remaining' in rv.headers)
        self.assertTrue('X-RateLimit-Limit' in rv.headers)
        self.assertTrue('X-RateLimit-Reset' in rv.headers)
        self.assertTrue(int(rv.headers['X-RateLimit-Limit']) == \
            int(rv.headers['X-RateLimit-Remaining']) + 1)
        while int(rv.headers['X-RateLimit-Remaining']) > 0:
            rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(self.catalog['registrations_url'])
        self.assertTrue(rv.status_code == 429)

    def test_expanded_collections(self):
        # create new students
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'susan'})
        self.assertTrue(rv.status_code == 201)
        susan_url = rv.headers['Location']

        rv, json = self.client.get(self.catalog['students_url'] +
                                   "?expand=1")
        self.assertTrue(rv.status_code == 200)
        print(json)
        self.assertTrue(json['students'][0]['name'] == 'susan')
        self.assertTrue(json['students'][0]['self_url'] == susan_url)

    def _create_test_students(self):
        # create several students
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'one'})
        self.assertTrue(rv.status_code == 201)
        one_url = rv.headers['Location']
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'two'})
        self.assertTrue(rv.status_code == 201)
        two_url = rv.headers['Location']
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'three'})
        self.assertTrue(rv.status_code == 201)
        three_url = rv.headers['Location']
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'four'})
        self.assertTrue(rv.status_code == 201)
        four_url = rv.headers['Location']
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'five'})
        self.assertTrue(rv.status_code == 201)
        five_url = rv.headers['Location']

        return [one_url, two_url, three_url, four_url, five_url]

    def test_filters(self):
        urls = self._create_test_students()

        # test various filter operators
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=name,eq,three')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[2]])

        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=name,ne,three&sort=id,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[0], urls[1], urls[3],
                                             urls[4]])

        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=id,le,2&sort=id,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[0], urls[1]])

        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=id,ge,2;id,lt,4&sort=id,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[1], urls[2]])

        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=name,in,three,five&sort=id,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[2], urls[4]])

        # bad operator is ignored
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=name,is,three,five')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['students']) == 5)

        # bad column name is ignored
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?filter=foo,in,three,five')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(len(json['students']) == 5)

    def test_sorting(self):
        urls = self._create_test_students()

        # sort ascending (implicit)
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?sort=name')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[4], urls[3], urls[0],
                                             urls[2], urls[1]])

        # sort ascending
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?sort=name,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[4], urls[3], urls[0],
                                             urls[2], urls[1]])

        # sort descending
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?sort=name,desc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(json['students'] == [urls[1], urls[2], urls[0],
                                             urls[3], urls[4]])

    def test_pagination(self):
        urls = self._create_test_students()

        # get collection in pages
        rv, json = self.client.get(self.catalog['students_url'] +
                                   '?page=1&per_page=2&sort=name,asc')
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(urls[4] in json['students'])
        self.assertTrue(urls[3] in json['students'])
        self.assertTrue(len(json['students']) == 2)
        self.assertTrue('total' in json['meta'])
        self.assertTrue(json['meta']['total'] == 5)
        self.assertTrue('prev_url' in json['meta'])
        self.assertTrue(json['meta']['prev_url'] is None)
        first_url = json['meta']['first_url']
        last_url = json['meta']['last_url']
        next_url = json['meta']['next_url']

        rv, json = self.client.get(first_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(urls[4] in json['students'])
        self.assertTrue(urls[3] in json['students'])
        self.assertTrue(len(json['students']) == 2)

        rv, json = self.client.get(next_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(urls[0] in json['students'])
        self.assertTrue(urls[2] in json['students'])
        self.assertTrue(len(json['students']) == 2)
        next_url = json['meta']['next_url']

        rv, json = self.client.get(next_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(urls[1] in json['students'])
        self.assertTrue(len(json['students']) == 1)

        rv, json = self.client.get(last_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(urls[1] in json['students'])
        self.assertTrue(len(json['students']) == 1)

    def test_etag(self):
        # create two students
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'one'})
        self.assertTrue(rv.status_code == 201)
        one_url = rv.headers['Location']
        rv, json = self.client.post(self.catalog['students_url'],
                                    data={'name': 'two'})
        self.assertTrue(rv.status_code == 201)
        two_url = rv.headers['Location']

        # get their etags
        rv, json = self.client.get(one_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue('Cache-Control' in rv.headers)
        one_etag = rv.headers['ETag']
        rv, json = self.client.get(two_url)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue('Cache-Control' in rv.headers)
        two_etag = rv.headers['ETag']

        # send If-None-Match header
        rv, json = self.client.get(one_url, headers={
            'If-None-Match': one_etag})
        self.assertTrue(rv.status_code == 304)
        rv, json = self.client.get(one_url, headers={
            'If-None-Match': one_etag + ', ' + two_etag})
        self.assertTrue(rv.status_code == 304)
        rv, json = self.client.get(one_url, headers={
            'If-None-Match': two_etag})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(one_url, headers={
            'If-None-Match': two_etag + ', *'})
        self.assertTrue(rv.status_code == 304)

        # send If-Match header
        rv, json = self.client.get(one_url, headers={
            'If-Match': one_etag})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(one_url, headers={
            'If-Match': one_etag + ', ' + two_etag})
        self.assertTrue(rv.status_code == 200)
        rv, json = self.client.get(one_url, headers={
            'If-Match': two_etag})
        self.assertTrue(rv.status_code == 412)
        rv, json = self.client.get(one_url, headers={
            'If-Match': '*'})
        self.assertTrue(rv.status_code == 200)

        # change a resource
        rv, json = self.client.put(one_url, data={'name': 'not-one'})
        self.assertTrue(rv.status_code == 200)

        # use stale etag
        rv, json = self.client.get(one_url, headers={
            'If-None-Match': one_etag})
        self.assertTrue(rv.status_code == 200)
