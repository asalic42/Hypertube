import requests

USER_AGENT = "Hypertube/1.0 (42 school project)"
DEFAULT_TIMEOUT = (5, 15)


def get(url, *, params=None, headers=None, timeout=DEFAULT_TIMEOUT):
    """GET with a project user agent and mandatory timeouts. Raises requests.RequestException."""
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def post(url, *, json=None, headers=None, timeout=DEFAULT_TIMEOUT):
    response = requests.post(
        url,
        json=json,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        timeout=timeout,
    )
    response.raise_for_status()
    return response
