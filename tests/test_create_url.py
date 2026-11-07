import json


def _event(body, base64=False):
    return {"body": body, "isBase64Encoded": base64}


def test_creates_short_link(aws):
    resp = aws["create"].lambda_handler(_event(json.dumps({"url": "https://example.com/hello"})), None)
    assert resp["statusCode"] == 201

    body = json.loads(resp["body"])
    assert len(body["code"]) == 7

    stored = aws["table"].get_item(Key={"short_code": body["code"]})["Item"]
    assert stored["long_url"] == "https://example.com/hello"
    assert stored["hits"] == 0


def test_accepts_base64_body(aws):
    import base64

    payload = base64.b64encode(json.dumps({"url": "https://example.com"}).encode()).decode()
    resp = aws["create"].lambda_handler(_event(payload, base64=True), None)
    assert resp["statusCode"] == 201


def test_rejects_bad_input(aws):
    bad_bodies = [
        None,
        "not json",
        json.dumps({}),
        json.dumps({"url": ""}),
        json.dumps({"url": "ftp://example.com"}),
        json.dumps({"url": "javascript:alert(1)"}),
        json.dumps({"url": "https://" + "a" * 3000}),
        json.dumps(["https://example.com"]),
        json.dumps({"url": 123}),
    ]
    for body in bad_bodies:
        resp = aws["create"].lambda_handler(_event(body), None)
        assert resp["statusCode"] == 400, body
