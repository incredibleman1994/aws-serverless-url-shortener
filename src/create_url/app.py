"""POST /api/shorten - validate a URL, store it in DynamoDB, return a short code."""
import base64
import json
import os
import secrets
import string
import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
TTL_DAYS = int(os.environ.get("TTL_DAYS", "365"))
CODE_LENGTH = 7
MAX_URL_LENGTH = 2048
MAX_ATTEMPTS = 5
ALPHABET = string.ascii_letters + string.digits

table = boto3.resource("dynamodb").Table(TABLE_NAME)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_url(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw).get("url", "").strip()


def _is_valid_url(url):
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def lambda_handler(event, context):
    try:
        long_url = _parse_url(event)
    except (ValueError, AttributeError):
        return _response(400, {"error": 'Body must be JSON like {"url": "https://example.com"}'})

    if not _is_valid_url(long_url):
        return _response(400, {"error": "Provide a valid http(s) URL (max 2048 characters)"})

    now = int(time.time())
    expires_at = now + TTL_DAYS * 86400

    # Retry on the (very unlikely) chance of a short-code collision.
    for _ in range(MAX_ATTEMPTS):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        try:
            table.put_item(
                Item={
                    "short_code": code,
                    "long_url": long_url,
                    "created_at": now,
                    "expires_at": expires_at,
                    "hits": 0,
                },
                ConditionExpression="attribute_not_exists(short_code)",
            )
            print(json.dumps({"event": "link_created", "short_code": code}))
            return _response(201, {"code": code, "long_url": long_url, "expires_at": expires_at})
        except ClientError as err:
            if err.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

    return _response(503, {"error": "Could not allocate a short code, please retry"})
