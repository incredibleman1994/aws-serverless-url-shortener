"""GET /r/{code} - look up a short code and redirect to the original URL."""
import json
import os
import re
import time

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
CODE_PATTERN = re.compile(r"[A-Za-z0-9]{7}")

table = boto3.resource("dynamodb").Table(TABLE_NAME)


def _not_found():
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Link not found or expired"}),
    }


def lambda_handler(event, context):
    code = (event.get("pathParameters") or {}).get("code", "")
    if not CODE_PATTERN.fullmatch(code):
        return _not_found()

    item = table.get_item(Key={"short_code": code}).get("Item")
    # DynamoDB TTL deletion is lazy (can take up to ~48h), so check expiry ourselves.
    if not item or int(item.get("expires_at", 0)) < time.time():
        return _not_found()

    try:
        table.update_item(
            Key={"short_code": code},
            UpdateExpression="ADD #h :one",
            ExpressionAttributeNames={"#h": "hits"},
            ExpressionAttributeValues={":one": 1},
        )
    except ClientError as err:  # analytics must never break a redirect
        print(json.dumps({"event": "hit_counter_failed", "error": str(err)}))

    return {
        "statusCode": 302,
        "headers": {"Location": item["long_url"], "Cache-Control": "no-store"},
        "body": "",
    }
