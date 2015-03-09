import os
import redis

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = 'secret'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'api.sqlite')
USE_TOKEN_AUTH = True

# enable rate limits only if redis is running
try:
    r = redis.Redis()
    r.ping()
    USE_RATE_LIMITS = True
except redis.ConnectionError:
    USE_RATE_LIMITS = False
