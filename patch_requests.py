import json
import os.path
from functools import partial
from unittest.mock import Mock, patch

from requests import Response


class PatchingError(Exception):
    pass


class patch_requests(object):
    methods = ['get', 'post', 'put', 'patch', 'delete', 'request']

    def __init__(self, responses=None, record=None):
        responses = responses or []

        if isinstance(responses, str):
            self.responses = load_responses_from_dir(responses)
        else:
            self.responses = list(responses)
        self.record = record
        self._counter = 0

    def build_mocked_response(self, data):
        status_code, resp = data

        response = Response()
        response.status_code = status_code

        if isinstance(resp, str):
            response._content = resp.encode()
        elif isinstance(resp, bytes):
            response._content = resp
        elif isinstance(resp, (dict, list)):
            response._content = json.dumps(resp).encode()
        else:
            raise NotImplementedError(
                f'Cannot build mocked response for type {resp.__class__}')

        return response

    def __enter__(self):
        def mock_side_effect(_actual_http_method, *args, **kwargs):
            if self._counter >= len(self.responses):
                if self.record:
                    return record(_actual_http_method, *args, **kwargs)
                else:
                    raise PatchingError(
                        'Unexpeced amount of requests (latest was '
                        f'{_actual_http_method.upper()} with '
                        f'args: {args} and kwargs: {kwargs})')
            expected_method, result = self.responses[self._counter]
            self._counter += 1

            if expected_method.lower() != _actual_http_method:
                raise PatchingError(
                    f'Expected method {expected_method.upper()}, '
                    f'got {_actual_http_method.upper()}')

            return self.build_mocked_response(result)

        def record(_actual_http_method, *args, **kwargs):
            getattr(self, f'{_actual_http_method}_requests_patcher').stop()
            getattr(self, f'{_actual_http_method}_session_patcher').stop()

            if _actual_http_method != 'request':
                getattr(self, 'request_requests_patcher').stop()
                getattr(self, 'request_session_patcher').stop()

            self._counter += 1

            import requests
            import datetime

            response = getattr(requests, _actual_http_method)(*args, **kwargs)

            with open(os.path.join(self.record, (
                    datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')
                    + f'-{self._counter}'
                    + f'-{_actual_http_method}'
                    + '.txt')), 'w') as f:
                f.write(f'{_actual_http_method}\nargs={args}\nkwargs={kwargs}\n')
                f.write(f'{response.status_code}\n')
                f.write(response.text)

            start_patchers(_actual_http_method)
            if _actual_http_method != 'request':
                start_patchers('request')
            return response

        def start_patchers(method):
            requests_patcher = patch(f'requests.{method}')
            mocked_method_call = requests_patcher.start()
            session_patcher = patch(
                f'requests.Session.{method}', new=mocked_method_call)
            mocked_session = session_patcher.start()

            setattr(self, f'{method}_requests_patcher', requests_patcher)
            setattr(self, f'{method}_session_patcher', session_patcher)
            setattr(self, f'mocked_{method}', mocked_method_call)

            mocked_method_call.side_effect = partial(mock_side_effect, method)

        for method in self.methods:
            start_patchers(method)
        return self

    def __exit__(self, exc_type, *exc):
        if exc_type == PatchingError:
            return

        for method in self.methods:
            getattr(self, f'{method}_requests_patcher').stop()
            getattr(self, f'{method}_session_patcher').stop()

            if self.record:
                continue

            actual_call_count = getattr(
                self, 'mocked_{}'.format(method)).call_count
            expected_calls = filter(
                lambda r: r[0].lower() == method, self.responses)
            expected_calls = list(expected_calls)
            expected_call_count = len(expected_calls)
            assert actual_call_count == expected_call_count, (
                f'expected {method.upper()} call count '
                f'{expected_call_count}, got {actual_call_count}')

        self.mocks = {method: getattr(self, f'mocked_{method}')
                      for method in self.methods}


def load_responses_from_dir(_dir):
    ret = []
    files = sorted(os.listdir(_dir))
    files = (f for f in files if f.endswith('.txt'))
    for file in files:
        with open(os.path.join(_dir, file)) as f:
            content = f.read()
            lines = content.split('\n', 4)
            assert len(lines) == 5
            method = lines[0].strip()
            status_code = int(lines[3])
            data = '\n'.join(lines[4:]).strip()
            ret.append((method, (status_code, data)))
    return ret
