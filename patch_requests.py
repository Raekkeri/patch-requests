from functools import partial
from unittest.mock import Mock, patch


class PatchingError(Exception):
    pass


class patch_requests(object):
    methods = ['get', 'post', 'put', 'patch', 'delete']

    def __init__(self, responses):
        self.responses = list(responses)
        self._counter = 0

    def build_mocked_response(self, data):
        status_code, resp = data
        mocked = Mock(status_code=status_code)

        if isinstance(resp, str):
            mocked.text = resp
        elif isinstance(resp, bytes):
            mocked.content = resp
        elif isinstance(resp, (dict, list)):
            mocked.json.return_value = resp
        else:
            raise NotImplementedError(
                f'Cannot build mocked response for type {resp.__class__}')

        return mocked

    def __enter__(self):
        def side_effect(_actual_http_method, *args, **kwargs):
            if self._counter >= len(self.responses):
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

        for method in self.methods:
            requests_patcher = patch(f'requests.{method}')
            mocked_method_call = requests_patcher.start()
            session_patcher = patch(
                f'requests.Session.{method}', new=mocked_method_call)
            mocked_session = session_patcher.start()

            setattr(self, f'{method}_requests_patcher', requests_patcher)
            setattr(self, f'{method}_session_patcher', session_patcher)
            setattr(self, f'mocked_{method}', mocked_method_call)
            mocked_method_call.side_effect = partial(side_effect, method)
        return self

    def __exit__(self, exc_type, *exc):
        if exc_type == PatchingError:
            return

        for method in self.methods:
            getattr(self, f'{method}_requests_patcher').stop()
            getattr(self, f'{method}_session_patcher').stop()
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
