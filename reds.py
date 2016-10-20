import redis

cfg = {'host': '127.0.0.1', 'port': 6379, 'db': 0}

r = redis.StrictRedis(**cfg)
# r.set('foo', 'bar')
print r.get('foo')
