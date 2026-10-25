"""Tiny stand-in for the parts of `requests` jtlearn uses (urllib only, no install needed)."""
import json as _json
import urllib.error
import urllib.request


class RequestException(Exception):
    def __init__(self, *a, response=None):
        super().__init__(*a)
        self.response = response


class HTTPError(RequestException):
    pass


class _Exc:
    RequestException = RequestException
    HTTPError = HTTPError
    Timeout = RequestException
    ConnectionError = RequestException


exceptions = _Exc


class Response:
    def __init__(self, status, body):
        self.status_code = status
        self.content = body
        self.text = body.decode("utf-8", "replace")

    def json(self):
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError("HTTP %d" % self.status_code, response=self)


def _do(method, url, json=None, timeout=10, **_):
    data = None
    headers = {}
    if json is not None:
        data = _json.dumps(json).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, r.read())
    except urllib.error.HTTPError as e:
        return Response(e.code, e.read())
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise RequestException(str(getattr(e, "reason", e)))


def get(url, **kw): return _do("GET", url, **kw)
def put(url, **kw): return _do("PUT", url, **kw)
def patch(url, **kw): return _do("PATCH", url, **kw)
def post(url, **kw): return _do("POST", url, **kw)
def delete(url, **kw): return _do("DELETE", url, **kw)
