import pytest

from bocadillo import API, HTTPError
from bocadillo.error_handlers import (
    error_to_media,
    error_to_text,
    error_to_html,
)


@pytest.mark.parametrize(
    "status",
    [
        "400 Bad Request",
        "401 Unauthorized",
        "403 Forbidden",
        "405 Method Not Allowed",
        "500 Internal Server Error",
        # Non-error codes are supported too. Be responsible.
        "200 OK",
        "201 Created",
        "202 Accepted",
        "204 No Content",
    ],
)
def test_if_http_error_is_raised_then_automatic_response_is_sent(
    api: API, status: str
):
    status_code, phrase = status.split(" ", 1)
    status_code = int(status_code)

    @api.route("/")
    async def index(req, res):
        raise HTTPError(status_code)

    response = api.client.get("/")
    assert response.status_code == status_code
    assert phrase in response.text


@pytest.mark.parametrize(
    "exception_cls", [KeyError, ValueError, AttributeError]
)
def test_custom_error_handler(api: API, exception_cls):
    called = False

    @api.error_handler(KeyError)
    def on_key_error(req, res, exc):
        nonlocal called
        res.text = "Oops!"
        called = True

    @api.route("/")
    async def index(req, res):
        raise exception_cls("foo")

    if exception_cls == KeyError:
        response = api.client.get("/")
        assert called
        assert response.status_code == 500
        assert response.text == "Oops!"
    else:
        response = api.client.get("/")
        assert response.status_code == 500
        assert not called


# Use in a test to run against multiple error details. See:
# https://docs.pytest.org/en/latest/fixture.html#parametrizing-fixtures
@pytest.fixture(params=["", "Nope!"])
def detail(request):
    return request.param


@pytest.mark.parametrize(
    "handler, content, expected",
    [
        (
            error_to_html,
            lambda res: res.text,
            lambda detail: "<h1>403 Forbidden</h1>{}".format(
                f"\n<p>{detail}</p>" if detail else ""
            ),
        ),
        (
            error_to_media,
            lambda res: res.json(),
            lambda detail: (
                {"error": "403 Forbidden", "detail": detail, "status": 403}
                if detail
                else {"error": "403 Forbidden", "status": 403}
            ),
        ),
        (
            error_to_text,
            lambda res: res.text,
            lambda detail: "403 Forbidden{}".format(
                f"\n{detail}" if detail else ""
            ),
        ),
    ],
)
def test_builtin_handlers(api: API, detail, handler, content, expected):
    api.add_error_handler(HTTPError, handler)

    @api.route("/")
    async def index(req, res):
        raise HTTPError(403, detail=detail)
        pass

    response = api.client.get("/")
    assert response.status_code == 403
    assert content(response) == expected(detail)
