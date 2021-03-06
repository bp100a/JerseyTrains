#!/usr/bin/python
from unittest import TestCase
from models import cloudredis
import fakeredis


class TestRedis(TestCase):
    """test our redis server setup & connection"""

    @staticmethod
    def dict_compare(d1: dict, d2: dict):
        d1_keys = set(d1.keys())
        d2_keys = set(d2.keys())
        intersect_keys = d1_keys.intersection(d2_keys)
        added = d1_keys - d2_keys
        removed = d2_keys - d1_keys
        modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
        same = set(o for o in intersect_keys if d1[o] == d2[o])
        return added, removed, modified, same

    def test_redis_setup(self):
        """verify redis server config for testing"""
        redis_host, redis_password, redis_port = cloudredis.read_configuration()
        assert redis_host == 'bogus.redis.endpoint'
        assert redis_password == 'bogus.redis.password'
        assert redis_port == 14405

    def test_redis_initialize_fake(self):
        """test that we can set the fake redis server"""
        fake = fakeredis.FakeStrictRedis()
        cloudredis.initialize_cloud_redis(injected_server=fake)
        assert cloudredis.REDIS_SERVER == fake

    def test_redis_initialize(self):
        """test that when starting up, our redis server isn't set"""
        cloudredis.REDIS_SERVER = None
        cloudredis.initialize_cloud_redis(injected_server=None)
        assert cloudredis.REDIS_SERVER

    def test_redis_initialize_subsequent(self):
        """test setting of the global redis server"""
        cloudredis.REDIS_SERVER = 'foobar'
        cloudredis.initialize_cloud_redis(injected_server=None)
        assert cloudredis.REDIS_SERVER == 'foobar'

    def test_redis_cache_station_list(self):
        """verify we can cache a station list and get it back correctly"""
        fake = fakeredis.FakeStrictRedis()
        cloudredis.initialize_cloud_redis(injected_server=fake)
        to_cache = {'CM': 'Chatham',
                    'NY': 'New York',
                    'SE': 'Secaucus'}

        cloudredis.cache_station_list(to_cache)

        just_cached = cloudredis.station_list()
        assert just_cached
        assert isinstance(just_cached, dict)
        added, removed, modified, same = TestRedis.dict_compare(just_cached, just_cached)
        assert same

    def test_redis_cache_no_station_list(self):
        """verify on start that the station list is empty"""
        fake = fakeredis.FakeStrictRedis()
        cloudredis.initialize_cloud_redis(injected_server=fake)

        just_cached = cloudredis.station_list()
        assert not just_cached

    def test_redis_cache_not_exists(self):
        """test that if we ask for a non-existent key that it doesn't exist """
        fake = fakeredis.FakeStrictRedis()
        cloudredis.initialize_cloud_redis(injected_server=fake)
        assert not cloudredis.exists('bogus_key')

    def test_redis_cache_exists(self):
        """test can cache a station list and it is correct"""
        fake = fakeredis.FakeStrictRedis()
        cloudredis.initialize_cloud_redis(injected_server=fake)
        assert not cloudredis.exists('station_list')
        to_cache = {'CM': 'Chatham',
                    'NY': 'New York',
                    'SE': 'Secaucus'}
        cloudredis.cache_station_list(to_cache)
        assert cloudredis.exists('station_list')
        cached_list = cloudredis.station_list()
        assert cached_list == to_cache
