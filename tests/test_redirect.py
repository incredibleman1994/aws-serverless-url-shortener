import time


def _event(code):
    return {"pathParameters": {"code": code}}


def _put(table, code, url="https://example.com", expires_in=3600):
    table.put_item(
        Item={"short_code": code, "long_url": url, "expires_at": int(time.time()) + expires_in, "hits": 0}
    )


def test_redirects_and_counts_hits(aws):
    _put(aws["table"], "abc1234", "https://example.com/target")

    resp = aws["redirect"].lambda_handler(_event("abc1234"), None)
    assert resp["statusCode"] == 302
    assert resp["headers"]["Location"] == "https://example.com/target"

    aws["redirect"].lambda_handler(_event("abc1234"), None)
    assert aws["table"].get_item(Key={"short_code": "abc1234"})["Item"]["hits"] == 2


def test_unknown_code_is_404(aws):
    assert aws["redirect"].lambda_handler(_event("zzzzzzz"), None)["statusCode"] == 404


def test_malformed_code_is_404(aws):
    for code in ["", "short", "waytoolongcode", "bad!code", None]:
        assert aws["redirect"].lambda_handler(_event(code or ""), None)["statusCode"] == 404
    assert aws["redirect"].lambda_handler({}, None)["statusCode"] == 404


def test_expired_link_is_404(aws):
    _put(aws["table"], "old1234", expires_in=-10)
    assert aws["redirect"].lambda_handler(_event("old1234"), None)["statusCode"] == 404
