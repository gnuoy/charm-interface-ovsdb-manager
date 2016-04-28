# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest
import mock

import requires


_hook_args = {}


def mock_hook(*args, **kwargs):

    def inner(f):
        # remember what we were passed.  Note that we can't actually determine
        # the class we're attached to, as the decorator only gets the function.
        _hook_args[f.__name__] = dict(args=args, kwargs=kwargs)
        return f
    return inner


class TestOVSDBManagerRequires(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_hook = mock.patch('charms.reactive.hook', mock_hook)
        cls._patched_hook_started = cls._patched_hook.start()
        # force requires to rerun the mock_hook decorator:
        reload(requires)

    @classmethod
    def tearDownClass(cls):
        cls._patched_hook.stop()
        cls._patched_hook_started = None
        cls._patched_hook = None
        # and fix any breakage we did to the module
        reload(requires)

    def setUp(self):
        self.ovsr = requires.OVSDBManagerRequires('some-relation', [])
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        self.ovsr = None
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch_kr(self, attr, return_value=None):
        mocked = mock.patch.object(self.ovsr, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_registered_hooks(self):
        # test that the hooks actually registered the relation expressions that
        # are meaningful for this interface: this is to handle regressions.
        # The keys are the function names that the hook attaches to.
        hook_patterns = {
            'changed': (
                ('{requires:ovsdb-manager}-relation-'
                 '{joined,changed,departed}'), ),
            'broken': ('{requires:ovsdb-manager}-relation-broken', ),
        }
        for k, v in _hook_args.items():
            self.assertEqual(hook_patterns[k], v['args'])

    def test_changed(self):
        self.patch_kr('set_state')
        self.patch_kr('remove_state')
        self.patch_kr('connection_string', 'connstr')
        self.ovsr.changed()
        self.set_state.assert_has_calls([
            mock.call('{relation_name}.connected'),
            mock.call('{relation_name}.access.available'),
        ])

    def test_changed_no_connection(self):
        self.patch_kr('set_state')
        self.patch_kr('remove_state')
        self.patch_kr('connection_string', None)
        self.ovsr.changed()
        self.set_state.assert_called_once_with('{relation_name}.connected')
        self.remove_state.assert_called_once_with(
            '{relation_name}.access.available'
        )

    def test_broken(self):
        self.patch_kr('remove_state')
        self.ovsr.broken()
        self.remove_state.assert_has_calls([
            mock.call('{relation_name}.connected'),
            mock.call('{relation_name}.access.available'),
        ])

    def test_connection_string(self):
        self.patch_kr('host', '10.0.0.10')
        self.patch_kr('port', '1234')
        self.patch_kr('protocol', 'soc')
        self.assertEqual(
            self.ovsr.connection_string(),
            "soc:10.0.0.10:1234"
        )
        self.patch_kr('protocol', None)
        self.assertEqual(self.ovsr.connection_string(), None)

    def test_connection_string_fallback(self):
        self.patch_kr('host', None)
        self.patch_kr('port', None)
        self.patch_kr('protocol', 'soc')
        self.patch_kr('private_address', '10.0.0.20')
        self.assertEqual(
            self.ovsr.connection_string(),
            "soc:10.0.0.20:6640"
        )
