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
