import random
import time
import unittest

try:
    range = xrange
except NameError: # pragma: NO COVER  (Python3)
    pass


class LRUCacheTests(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.lru import LRUCache
        return LRUCache

    def check_cache_is_consistent(self, cache):
        """Return if cache is consistent, else raise fail test case."""
        # cache.hand/maxpos/size
        self.assertTrue(cache.hand < len(cache.clock_keys))
        self.assertTrue(cache.hand >= 0)
        self.assertEqual(cache.maxpos, cache.size - 1)
        self.assertEqual(len(cache.clock_keys), cache.size)

        # lengths of data structures
        self.assertEqual(len(cache.clock_keys), len(cache.clock_refs))
        self.assertTrue(len(cache.data) <= len(cache.clock_refs))

        # For each item in cache.data
        #   1. pos must be a valid index
        #   2. clock_keys must point back to the entry
        for key, value in cache.data.items():
            pos, val = value
            self.assertTrue(
                    type(pos) == type(42) or
                    type(pos) == type(2 ** 128))
            self.assertTrue(pos >= 0)
            self.assertTrue(pos <= cache.maxpos)

            clock_key = cache.clock_keys[pos]
            self.assertTrue(clock_key is key)
            clock_ref = cache.clock_refs[pos]

        # All clock_refs must be True or False, nothing else.
        for clock_ref in cache.clock_refs:
            self.assertTrue(clock_ref is True or clock_ref is False)

    def _makeOne(self, size):
        return self._getTargetClass()(size)

    def test_size_lessthan_1(self):
        self.assertRaises(ValueError, self._makeOne, 0)

    def test_get(self):
        cache = self._makeOne(1)
        # Must support different types of keys
        self.assertEqual(cache.get("foo"), None)
        self.assertEqual(cache.get(42), None)
        self.assertEqual(cache.get(("foo", 42)), None)
        self.assertEqual(cache.get(None), None)
        self.assertEqual(cache.get(""), None)
        self.assertEqual(cache.get(object()), None)
        # Check if default value is used
        self.assertEqual(cache.get("foo", "bar"), "bar")
        self.assertEqual(cache.get("foo", default="bar"), "bar")

        self.check_cache_is_consistent(cache)

    def test_put(self):
        cache = self._makeOne(8)
        self.check_cache_is_consistent(cache)
        # Must support different types of keys
        cache.put("foo", "FOO")
        cache.put(42, "fortytwo")
        cache.put( ("foo", 42), "tuple_as_key")
        cache.put(None, "None_as_key")
        cache.put("", "empty_string_as_key")
        cache.put(3.141, "float_as_key")
        my_object = object()
        cache.put(my_object, "object_as_key")

        self.check_cache_is_consistent(cache)

        self.assertEqual(cache.get("foo"), "FOO")
        self.assertEqual(cache.get(42), "fortytwo")
        self.assertEqual(cache.get(("foo", 42), "fortytwo"), "tuple_as_key")
        self.assertEqual(cache.get(None), "None_as_key")
        self.assertEqual(cache.get(""), "empty_string_as_key")
        self.assertEqual(cache.get(3.141), "float_as_key")
        self.assertEqual(cache.get(my_object), "object_as_key")

        # put()ing again must overwrite
        cache.put(42, "fortytwo again")
        self.assertEqual(cache.get(42), "fortytwo again")

        self.check_cache_is_consistent(cache)

    def test_invalidate(self):
        cache = self._makeOne(3)
        cache.put("foo", "bar")
        cache.put("FOO", "BAR")

        cache.invalidate("foo")
        self.assertEqual(cache.get("foo"), None)
        self.assertEqual(cache.get("FOO"), "BAR")
        self.check_cache_is_consistent(cache)

        cache.invalidate("FOO")
        self.assertEqual(cache.get("foo"), None)
        self.assertEqual(cache.get("FOO"), None)
        self.assertEqual(cache.data, {})
        self.check_cache_is_consistent(cache)

        cache.put("foo", "bar")
        cache.invalidate("nonexistingkey")
        self.assertEqual(cache.get("foo"), "bar")
        self.assertEqual(cache.get("FOO"), None)
        self.check_cache_is_consistent(cache)

    def test_small_cache(self):
        """Cache of size 1 must work"""
        cache = self._makeOne(1)

        cache.put("foo", "bar")
        self.assertEqual(cache.get("foo"), "bar")
        self.check_cache_is_consistent(cache)

        cache.put("FOO", "BAR")
        self.assertEqual(cache.get("FOO"), "BAR")
        self.assertEqual(cache.get("foo"), None)
        self.check_cache_is_consistent(cache)

        # put() again
        cache.put("FOO", "BAR")
        self.assertEqual(cache.get("FOO"), "BAR")
        self.assertEqual(cache.get("foo"), None)
        self.check_cache_is_consistent(cache)

        # invalidate()
        cache.invalidate("FOO")
        self.check_cache_is_consistent(cache)
        self.assertEqual(cache.get("FOO"), None)
        self.assertEqual(cache.get("foo"), None)

        # clear()
        cache.put("foo", "bar")
        self.assertEqual(cache.get("foo"), "bar")
        cache.clear()
        self.check_cache_is_consistent(cache)
        self.assertEqual(cache.get("FOO"), None)
        self.assertEqual(cache.get("foo"), None)

    def test_equal_but_not_identical(self):
        """equal but not identical keys must be treated the same"""
        cache = self._makeOne(1)
        tuple_one = (1, 1)
        tuple_two = (1, 1)
        cache.put(tuple_one, 42)

        self.assertEqual(cache.get(tuple_one), 42)
        self.assertEqual(cache.get(tuple_two), 42)
        self.check_cache_is_consistent(cache)

        cache = self._makeOne(1)
        cache.put(tuple_one, 42)
        cache.invalidate(tuple_two)
        self.assertEqual(cache.get(tuple_one), None)
        self.assertEqual(cache.get(tuple_two), None)

    def test_perfect_hitrate(self):
        """If cache size equals number of items, expect 100% cache hits"""
        size = 1000
        cache = self._makeOne(size)

        for count in range(size):
            cache.put(count, "item%s" % count)

        for cache_op in range(10000):
            item = random.randrange(0, size - 1)
            if random.getrandbits(1):
                self.assertEqual(cache.get(item), "item%s" % item)
            else:
                cache.put(item, "item%s" % item)

        self.assertEqual(cache.misses, 0)
        self.assertEqual(cache.evictions, 0)

        self.check_cache_is_consistent(cache)

    def test_imperfect_hitrate(self):
        """If cache size == half the number of items -> hit rate ~50%"""
        size = 1000
        cache = self._makeOne(size / 2)

        for count in range(size):
            cache.put(count, "item%s" % count)

        hits = 0
        misses = 0
        total_gets = 0
        for cache_op in range(10000):
            item = random.randrange(0, size - 1)
            if random.getrandbits(1):
                entry = cache.get(item)
                total_gets += 1
                self.assertTrue(
                        (entry == "item%s" % item) or
                        entry is None)
                if entry is None:
                    misses += 1
                else:
                    hits += 1
            else:
                cache.put(item, "item%s" % item)

        # Cache hit rate should be roughly 50%
        hit_ratio = hits / float(total_gets) * 100
        self.assertTrue(hit_ratio > 45)
        self.assertTrue(hit_ratio < 55)

        # The internal cache counters should have the same information
        internal_hit_ratio = 100 * cache.hits / cache.lookups
        self.assertTrue(internal_hit_ratio > 45)
        self.assertTrue(internal_hit_ratio < 55)

        # The internal miss counters should also be around 50%
        internal_miss_ratio = 100 * cache.misses / cache.lookups
        self.assertTrue(internal_miss_ratio > 45)
        self.assertTrue(internal_miss_ratio < 55)

        self.check_cache_is_consistent(cache)

    def test_eviction_counter(self):
        cache = self._makeOne(2)
        cache.put(1, 1)
        cache.put(2, 1)
        self.assertEqual(cache.evictions, 0)

        cache.put(3, 1)
        cache.put(4, 1)
        self.assertEqual(cache.evictions, 2)

        cache.put(3, 1)
        cache.put(4, 1)
        self.assertEqual(cache.evictions, 2)

        cache.clear()
        self.assertEqual(cache.evictions, 0)


    def test_it(self):
        cache = self._makeOne(3)
        self.assertEqual(cache.get('a'), None)

        cache.put('a', '1')
        pos, value = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'a')
        self.assertEqual(value, '1')
        self.assertEqual(cache.get('a'), '1')
        self.assertEqual(cache.hand, pos + 1)

        pos, value = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.hand, pos + 1)
        self.assertEqual(len(cache.data), 1)

        cache.put('b', '2')
        pos, value = cache.data.get('b')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'b')
        self.assertEqual(len(cache.data), 2)

        cache.put('c', '3')
        pos, value = cache.data.get('c')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'c')
        self.assertEqual(len(cache.data), 3)

        pos, value = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)

        cache.get('a')
        # All items have ref==True. cache.hand points to "a". Putting
        # "d" will set ref=False on all items and then replace "a",
        # because "a" is the first item with ref==False that is found.
        cache.put('d', '4')
        self.assertEqual(len(cache.data), 3)
        self.assertEqual(cache.data.get('a'), None)

        # Only item "d" has ref==True. cache.hand points at "b", so "b"
        # will be evicted when "e" is inserted. "c" will be left alone.
        cache.put('e', '5')
        self.assertEqual(len(cache.data), 3)
        self.assertEqual(cache.data.get('b'), None)
        self.assertEqual(cache.get('d'), '4')
        self.assertEqual(cache.get('e'), '5')
        self.assertEqual(cache.get('a'), None)
        self.assertEqual(cache.get('b'), None)
        self.assertEqual(cache.get('c'), '3')

        self.check_cache_is_consistent(cache)


class ExpiringLRUCacheTests(LRUCacheTests):

    def _getTargetClass(self):
        from repoze.lru import ExpiringLRUCache
        return ExpiringLRUCache

    def _makeOne(self, size, default_timeout=None):
        if default_timeout is None:
            return self._getTargetClass()(size)
        else:
            return self._getTargetClass()(size, default_timeout=default_timeout)

    def check_cache_is_consistent(self, cache):
        """Return if cache is consistent, else raise fail test case.

        This is slightly different for ExpiringLRUCache since self.data
        contains 3-tuples instead of 2-tuples.
        """
        # cache.hand/maxpos/size
        self.assertTrue(cache.hand < len(cache.clock_keys))
        self.assertTrue(cache.hand >= 0)
        self.assertEqual(cache.maxpos, cache.size - 1)
        self.assertEqual(len(cache.clock_keys), cache.size)

        # lengths of data structures
        self.assertEqual(len(cache.clock_keys), len(cache.clock_refs))
        self.assertTrue(len(cache.data) <= len(cache.clock_refs))

        # For each item in cache.data
        #   1. pos must be a valid index
        #   2. clock_keys must point back to the entry
        for key, value in cache.data.items():
            pos, val, timeout = value
            self.assertTrue(
                type(pos) == type(42) or type(pos) == type(2 ** 128))
            self.assertTrue(pos >= 0)
            self.assertTrue(pos <= cache.maxpos)

            clock_key = cache.clock_keys[pos]
            self.assertTrue(clock_key is key)
            clock_ref = cache.clock_refs[pos]

            self.assertTrue(type(timeout) == type(3.141))

        # All clock_refs must be True or False, nothing else.
        for clock_ref in cache.clock_refs:
            self.assertTrue(clock_ref is True or clock_ref is False)

    def test_it(self):
        """Test a sequence of operations

        Looks at internal data, which is different for ExpiringLRUCache.
        """
        cache = self._makeOne(3)
        self.assertEqual(cache.get('a'), None)

        cache.put('a', '1')
        pos, value, expires = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'a')
        self.assertEqual(value, '1')
        self.assertEqual(cache.get('a'), '1')
        self.assertEqual(cache.hand, pos + 1)

        pos, value, expires = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.hand, pos + 1)
        self.assertEqual(len(cache.data), 1)

        cache.put('b', '2')
        pos, value, expires = cache.data.get('b')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'b')
        self.assertEqual(len(cache.data), 2)

        cache.put('c', '3')
        pos, value, expires = cache.data.get('c')
        self.assertEqual(cache.clock_refs[pos], True)
        self.assertEqual(cache.clock_keys[pos], 'c')
        self.assertEqual(len(cache.data), 3)

        pos, value, expires = cache.data.get('a')
        self.assertEqual(cache.clock_refs[pos], True)

        cache.get('a')
        # All items have ref==True. cache.hand points to "a". Putting
        # "d" will set ref=False on all items and then replace "a",
        # because "a" is the first item with ref==False that is found.
        cache.put('d', '4')
        self.assertEqual(len(cache.data), 3)
        self.assertEqual(cache.data.get('a'), None)

        # Only item "d" has ref==True. cache.hand points at "b", so "b"
        # will be evicted when "e" is inserted. "c" will be left alone.
        cache.put('e', '5')
        self.assertEqual(len(cache.data), 3)
        self.assertEqual(cache.data.get('b'), None)
        self.assertEqual(cache.get('d'), '4')
        self.assertEqual(cache.get('e'), '5')
        self.assertEqual(cache.get('a'), None)
        self.assertEqual(cache.get('b'), None)
        self.assertEqual(cache.get('c'), '3')

        self.check_cache_is_consistent(cache)

    def test_default_timeout(self):
        """Default timeout provided at init time must be applied"""
        # Provide no default timeout -> entries must remain valid
        cache = self._makeOne(3)
        cache.put("foo", "bar")

        time.sleep(0.1)
        cache.put("FOO", "BAR")
        self.assertEqual(cache.get("foo"), "bar")
        self.assertEqual(cache.get("FOO"), "BAR")
        self.check_cache_is_consistent(cache)

        # Provide short default timeout -> entries must become invalid
        cache = self._makeOne(3, default_timeout=0.1)
        cache.put("foo", "bar")

        time.sleep(0.1)
        cache.put("FOO", "BAR")
        self.assertEqual(cache.get("foo"), None)
        self.assertEqual(cache.get("FOO"), "BAR")
        self.check_cache_is_consistent(cache)

    def test_different_timeouts(self):
        """Timeouts must be per entry, default applied when none provided"""
        cache = self._makeOne(3, default_timeout=0.1)

        cache.put("one", 1)
        cache.put("two", 2, timeout=0.2)
        cache.put("three", 3, timeout=0.3)

        # All entries still here
        self.assertEqual(cache.get("one"), 1)
        self.assertEqual(cache.get("two"), 2)
        self.assertEqual(cache.get("three"), 3)

        # Entry "one" must expire, "two"/"three" remain valid
        time.sleep(0.1)
        self.assertEqual(cache.get("one"), None)
        self.assertEqual(cache.get("two"), 2)
        self.assertEqual(cache.get("three"), 3)

        # Only "three" remains valid
        time.sleep(0.1)
        self.assertEqual(cache.get("one"), None)
        self.assertEqual(cache.get("two"), None)
        self.assertEqual(cache.get("three"), 3)

        # All have expired
        time.sleep(0.1)
        self.assertEqual(cache.get("one"), None)
        self.assertEqual(cache.get("two"), None)
        self.assertEqual(cache.get("three"), None)

        self.check_cache_is_consistent(cache)

    def test_renew_timeout(self):
        """Re-putting an entry must update timeout"""
        cache = self._makeOne(3, default_timeout=0.2)

        cache.put("foo", "bar")
        cache.put("foo2", "bar2", timeout=10)
        cache.put("foo3", "bar3", timeout=10)

        time.sleep(0.1)
        # All must still be here
        self.assertEqual(cache.get("foo"), "bar")
        self.assertEqual(cache.get("foo2"), "bar2")
        self.assertEqual(cache.get("foo3"), "bar3")
        self.check_cache_is_consistent(cache)

        # Set new timeouts by re-put()ing the entries
        cache.put("foo", "bar")
        cache.put("foo2", "bar2", timeout=0.1)
        cache.put("foo3", "bar3")

        time.sleep(0.1)
        # "foo2" must have expired
        self.assertEqual(cache.get("foo"), "bar")
        self.assertEqual(cache.get("foo2"), None)
        self.assertEqual(cache.get("foo3"), "bar3")
        self.check_cache_is_consistent(cache)


class DecoratorTests(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.lru import lru_cache
        return lru_cache

    def _makeOne(self, maxsize, cache, timeout=None):
        return self._getTargetClass()(maxsize, timeout=timeout, cache=cache)

    def test_ctor_nocache(self):
        decorator = self._makeOne(10, None)
        self.assertEqual(decorator.cache.size, 10)

    def test_singlearg(self):
        cache = DummyLRUCache()
        decorator = self._makeOne(0, cache)
        def wrapped(key):
            return key
        decorated = decorator(wrapped)
        result = decorated(1)
        self.assertEqual(cache[(1,)], 1)
        self.assertEqual(result, 1)
        self.assertEqual(len(cache), 1)
        result = decorated(2)
        self.assertEqual(cache[(2,)], 2)
        self.assertEqual(result, 2)
        self.assertEqual(len(cache), 2)
        result = decorated(2)
        self.assertEqual(cache[(2,)], 2)
        self.assertEqual(result, 2)
        self.assertEqual(len(cache), 2)

    def test_multiargs(self):
        cache = DummyLRUCache()
        decorator = self._makeOne(0, cache)
        def moreargs(*args):
            return args
        decorated = decorator(moreargs)
        result = decorated(3, 4, 5)
        self.assertEqual(cache[(3, 4, 5)], (3, 4, 5))
        self.assertEqual(result, (3, 4, 5))
        self.assertEqual(len(cache), 1)

    def test_expiry(self):
        """When timeout is given, decorator must eventually forget entries"""
        @self._makeOne(1, None, timeout=0.1)
        def sleep_a_bit(param):
            time.sleep(0.1)
            return 2 * param

        # First call must take at least 0.1 seconds
        start = time.time()
        result1 = sleep_a_bit("hello")
        stop = time.time()
        self.assertEqual(result1, 2 * "hello")
        self.assertTrue(stop - start > 0.1)

        # Second call must take less than 0.1 seconds.
        start = time.time()
        result2 = sleep_a_bit("hello")
        stop = time.time()
        self.assertEqual(result2, 2 * "hello")
        self.assertTrue(stop - start < 0.1)

        time.sleep(0.1)
        # This one must calculate again and take at least 0.1 seconds
        start = time.time()
        result3 = sleep_a_bit("hello")
        stop = time.time()
        self.assertEqual(result3, 2 * "hello")
        self.assertTrue(stop - start > 0.1)


class DummyLRUCache(dict):

    def put(self, k, v):
        return self.__setitem__(k, v)


class CacherMaker(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.lru import CacheMaker
        return CacheMaker

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_named_cache(self):
        maker = self._makeOne()
        size = 10
        name = "name"
        decorated = maker.lrucache(maxsize=size, name=name)(_adder)
        self.assertEqual(list(maker._cache.keys()), [name])
        self.assertEqual(maker._cache[name].size, size)
        decorated(10)
        decorated(11)
        self.assertEqual(len(maker._cache[name].data),2)

    def test_exception(self):
        maker = self._makeOne()
        size = 10
        name = "name"
        decorated = maker.lrucache(maxsize=size, name=name)(_adder)
        self.assertRaises(KeyError, maker.lrucache, maxsize=size, name=name)
        self.assertRaises(ValueError, maker.lrucache)

    def test_defaultvalue_and_clear(self):
        size = 10
        maker = self._makeOne(maxsize=size)
        for i in range(100):
            decorated = maker.lrucache()(_adder)
            decorated(10)

        self.assertEqual(len(maker._cache) , 100)
        for _cache in maker._cache.values():
            self.assertEqual( _cache.size,size)
            self.assertEqual(len(_cache.data),1)
        ## and test clear cache
        maker.clear()
        for _cache in maker._cache.values():
            self.assertEqual( _cache.size,size)
            self.assertEqual(len(_cache.data),0)

    def test_clear_with_single_name(self):
        maker = self._makeOne(maxsize=10)
        one = maker.lrucache(name='one')(_adder)
        two = maker.lrucache(name='two')(_adder)
        for i in range(100):
            _ = one(i)
            _ = two(i)
        self.assertEqual(len(maker._cache['one'].data), 10)
        self.assertEqual(len(maker._cache['two'].data), 10)
        maker.clear('one')
        self.assertEqual(len(maker._cache['one'].data), 0)
        self.assertEqual(len(maker._cache['two'].data), 10)

    def test_clear_with_multiple_names(self):
        maker = self._makeOne(maxsize=10)
        one = maker.lrucache(name='one')(_adder)
        two = maker.lrucache(name='two')(_adder)
        three = maker.lrucache(name='three')(_adder)
        for i in range(100):
            _ = one(i)
            _ = two(i)
            _ = three(i)
        self.assertEqual(len(maker._cache['one'].data), 10)
        self.assertEqual(len(maker._cache['two'].data), 10)
        self.assertEqual(len(maker._cache['three'].data), 10)
        maker.clear('one', 'three')
        self.assertEqual(len(maker._cache['one'].data), 0)
        self.assertEqual(len(maker._cache['two'].data), 10)
        self.assertEqual(len(maker._cache['three'].data), 0)

    def test_expiring(self):
        size = 10
        timeout = 10
        name = "name"
        cache = self._makeOne(maxsize=size, timeout=timeout)
        for i in range(100):
            if not i:
                decorated = cache.expiring_lrucache(name=name)(_adder)
                self.assertEqual( cache._cache[name].size,size)
            else:
                decorated = cache.expiring_lrucache()(_adder)
            decorated(10)

        self.assertEqual( len(cache._cache) , 100)
        for _cache in cache._cache.values():
            self.assertEqual( _cache.size,size)
            self.assertEqual( _cache.default_timeout,timeout)
            self.assertEqual(len(_cache.data),1)
        ## and test clear cache
        cache.clear()
        for _cache in cache._cache.values():
            self.assertEqual( _cache.size,size)
            self.assertEqual(len(_cache.data),0)

def _adder(x):
    return x + 10
