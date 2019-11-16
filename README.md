# patch-requests

Simple patching of `requests` calls.

The package contains a `patch_requests` context manager, which can be used to
mock one or multiple calls to `requests.FOO()` methods. Also calls to
`requests.Session().FOO()` are mocked automatically.

The `patch_requests` context manager takes a list of expected HTTP methods to
be called, as well as their expected status codes and returned data. A single
expected call is a tuple of `("method", ("status_code (int)",
"returned_data (either dict, str or bytes)"))`. E.g.:

```Python
with patch_requests([('get', (200, {'ids': [1, 3, 4]}))]) as cm:
    assert requests.get('http://whatever').json() == {'ids': [1, 3, 4]}
```

Some assumptions are made based on the type of given "returned data":

- if type is `dict`, the return value of `response.json()` is set to the given value
- if type is `str`, the `response.text` is set to the given value
- if type is `bytes`, the `response.content` is set to the given value.

Upon exiting the `patch_requests` context, it is possible to access the mocks of
each `requests` calls with `cm.mocks`, which is a dictionary with method names as keys.
For example:

```Python
with patch_requests([('get', (200, {'ids': [1, 3, 4]}))]) as cm:
    assert requests.get('http://whatever').json() == {'ids': [1, 3, 4]}
assert cm.mocks['get'].call_args_list[0][0][0] == 'http://whatever'
```


A full example from tests.py:

```Python
import unittest
import requests
from patch_requests import patch_requests

class TestPatcher(unittest.TestCase):
    def test_multiple_requests(self):
        with patch_requests([
                ('get', (200, {1: 1})),
                ('post', (201, {2: 2})),
                ('GET', (404, '<html><p><br/>')),
                ('patch', (500, b'\\')),
                ]) as p:
            response = requests.get('http://example.com')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {1: 1})

            s = requests.Session()

            response = s.post('http://www.example.com')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json(), {2: 2})

            response = s.get('http://')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.text, '<html><p><br/>')

            s.close()

            response = requests.patch('')
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.content, b'\\')

        self.assertEqual(
            p.mocks['get'].call_args_list[0][0], ('http://example.com',))
        self.assertEqual(
            p.mocks['post'].call_args_list[0][0], ('http://www.example.com',))
```
