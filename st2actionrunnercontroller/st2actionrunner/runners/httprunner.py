import requests
import uuid

from oslo.config import cfg

from st2actionrunner.runners import ActionRunner
from st2common import log as logging

LOG = logging.getLogger(__name__)


# Lookup constants for runner params
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_URL = 'url'
RUNNER_HEADERS = 'headers'  # Debatable whether this should be action params.
RUNNER_COOKIES = 'cookies'
RUNNER_ALLOW_REDIRECTS = 'allow_redirects'
RUNNER_PROXIES = 'proxies'


# Lookup constants for action params
ACTION_AUTH = 'auth'
ACTION_BODY = 'body'
ACTION_TIMEOUT = 'timeout'
ACTION_METHOD = 'method'
ACTION_QUERY_PARAMS = 'params'


def get_runner():
    return HttpRunner(str(uuid.uuid4()))


class HttpRunner(ActionRunner):
    def __init__(self, id):
        super(HttpRunner, self).__init__()
        self._on_behalf_user = cfg.CONF.ssh_runner.user
        self._timeout = 60

    def pre_run(self):
        LOG.debug('Entering HttpRunner.pre_run() for liveaction_id="%s"', self.liveaction_id)
        LOG.debug('    runner_parameters = %s', self.runner_parameters)
        self._on_behalf_user = self.runner_parameters.get(RUNNER_ON_BEHALF_USER,
                                                          self._on_behalf_user)
        self._url = self.runner_parameters.get(RUNNER_URL, None)
        self._headers = self.runner_parameters.get(RUNNER_HEADERS, {})
        self._cookies = self.runner_parameters.get(RUNNER_COOKIES, None)
        self._redirects = self.runner_parameters.get(RUNNER_ALLOW_REDIRECTS, False)
        self._proxies = self.runner_parameters.get(RUNNER_PROXIES, None)
        return

    def run(self, action_parameters):
        client = self._get_http_client(action_parameters)
        LOG.debug('action_parameters = %s', action_parameters)
        try:
            output = client.run()
        except Exception:
            raise
        self.container_service.report_result(output)
        return output is not None

    def post_run(self):
        pass

    def _get_http_client(self, action_parameters):
        # XXX: Action context should be passed in and we need to add x-headers here.
        body = action_parameters.get(ACTION_BODY, None)
        timeout = float(action_parameters.get(ACTION_TIMEOUT, self._timeout))
        method = action_parameters.get(ACTION_METHOD, 'GET')
        params = action_parameters.get(ACTION_QUERY_PARAMS, None)
        auth = action_parameters.get('ACTION_AUTH', {})
        return HTTPClient(url=self._url, method=method, body=body, params=params,
                          headers=self._headers, cookies=self._cookies, auth=auth,
                          timeout=timeout, allow_redirects=self._redirects,
                          proxies=self._proxies)


class HTTPClient(object):
    def __init__(self, url=None, method=None, body='', params=None, headers=None, cookies=None,
                 auth=None, timeout=60, allow_redirects=True, proxies=None):
        if url is None:
            raise Exception('URL must be specified.')
        self.url = url
        if method is None:
            method = 'GET'
        self.method = method
        self.headers = headers
        self.body = body
        self.params = params
        self.headers = headers
        self.cookies = cookies
        self.auth = auth
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.proxies = proxies

    def run(self):
        results = {}
        try:
            resp = requests.request(
                self.method,
                self.url,
                params=self.params,
                data=self.body,
                headers=self.headers,
                cookies=self.cookies,
                auth=self.auth,
                timeout=self.timeout,
                allow_redirects=self.allow_redirects,
                proxies=self.proxies
            )
            results['status_code'] = resp.status_code
            results['body'] = resp.text
            results['headers'] = dict(resp.headers)
            return results
        except Exception as e:
            LOG.exception('Exception making request to remote URL: %s, %s', self.url, e)
            raise
        finally:
            resp.close()
