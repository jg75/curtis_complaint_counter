"""Tests for complaint_counter.py."""
from hashlib import sha256
import hmac
import json
import os
import time
from unittest.mock import MagicMock, Mock
from urllib.parse import urlencode

import pytest

import complaint_counter.aws_lambda
from complaint_counter import lambda_handler


def make_request(body=None, headers=None, *, secret=None, timestamp=None):
    """Create a request that resembles a slack-API request.

    By default, this function returns a valid request that should result in a
    200 OK.

    To specify the lack of a default header, specify None as it's value.
    """
    body = body if body else dict()
    headers = headers if headers else dict()
    timestamp = timestamp if timestamp else int(time.time())
    secret = secret if secret else "8f742231b10e8888abcd99yyyzzz85a5"

    body.setdefault("token", "ftMJyTJlA4qo8QNY3PVhuYf6")
    body.setdefault("team_id", "T18UTUL93")
    body.setdefault("team_domain", "disjointedimages")
    body.setdefault("channel_id", "D81P2TLNM")
    body.setdefault("channel_name", "directmessage")
    body.setdefault("user_id", "U81JYT64Q")
    body.setdefault("user_name", "maxwellgbrown")
    body.setdefault("command", "/curtis_complained")
    body.setdefault("text", "")
    body.setdefault(
        "response_url",
        "https://hooks.slack.com/commands/T18UTUL93/440741347573"
        "/RSYHp7T18s0uP4eU7hGFdSm6",
    )

    # remove None values
    body = {k: v for k, v in body.items() if v is not None}

    urlencoded_body = urlencode(body)

    headers.setdefault("X-Slack-Request-Timestamp", timestamp)

    raw_signature = f"v0:{timestamp}:{urlencoded_body}"
    signature_hmac = hmac.new(secret.encode(), raw_signature.encode(), sha256)
    signature = b"v0=" + signature_hmac.hexdigest().encode()

    headers.setdefault("X-Slack-Signature", signature.decode())

    # remove None values
    headers = {k: v for k, v in headers.items() if v is not None}

    return {
        "body": urlencoded_body,
        "headers": headers,
    }


@pytest.fixture(autouse=True)
def dynamodb(monkeypatch):
    """Mock away the dynamodb client used by lambda_handler."""
    # boto3 is not installed for testing
    monkeypatch.setattr(complaint_counter.aws_lambda, 'boto3', Mock(),
                        raising=False)

    dynamodb = MagicMock()
    monkeypatch.setattr(complaint_counter.aws_lambda, 'dynamodb', dynamodb)
    return dynamodb


@pytest.fixture(autouse=True)
def environment_variables(monkeypatch):
    """Set environment variables to be expected by the AWS Lambda handler."""
    environment = {"SIGNING_SECRET": "8f742231b10e8888abcd99yyyzzz85a5"}
    monkeypatch.setattr(os, 'environ', environment)


def test_lambda_handler_returns_200():
    """Test that lambda_handler returns a 200 status code."""
    request = make_request()
    response = lambda_handler(request)
    assert response['statusCode'] == 200


def test_lambda_handler_quotes_the_complaint():
    """Test that the lambda_handler returns the complaint as a quote."""
    complaint = "about foo and bar"

    request_body = {"text": complaint}
    request = make_request(request_body)

    response = lambda_handler(request)

    assert f'\n> {complaint}' in json.loads(response['body'])['text']


def test_lambda_handler_saves_complaints_to_storage(dynamodb):
    """Tests that lambda_handler saves complaints."""
    text = "dynamo db serializes objects"
    username = "johnquincyadams"

    body = {"text": text, "user_name": username}
    request = make_request(body)

    lambda_handler(request)

    assert len(dynamodb.put_item.mock_calls) == 1
    args, kwargs = dynamodb.put_item.call_args

    item = kwargs["Item"]
    assert item["uuid"]["S"]
    assert item["timestamp"]["N"]
    assert item["reporter"]["S"] == username
    assert item["complaint"]["S"] == text


def test_lambda_handler_returns_a_total_number_of_complaints(dynamodb):
    """Tests that lambda_handler is counting the complaints."""
    count = 774
    dynamodb.scan.return_value = {"Count": 774}

    request = make_request()
    response = lambda_handler(request)

    response_text = json.loads(response['body'])['text']
    assert f"\nCurtis has *{count}* recorded complaints." in response_text


def test_lambda_handler_returns_a_channel_visible_response():
    """Tests that lambda_handler yells curtis's complaints to the channel."""
    request = make_request()
    response = lambda_handler(request)

    assert json.loads(response['body'])['response_type'] == 'in_channel'


@pytest.mark.parametrize("required_header", [
    "X-Slack-Signature",
    "X-Slack-Request-Timestamp",
])
def test_lambda_handler_returns_403_with_no_slack_auth_header(required_header):
    """Tests that missing slack auth headers causes HTTP 403."""
    headers = {required_header: None}
    request = make_request(headers=headers)

    response = lambda_handler(request)

    assert response["statusCode"] == 403
    response_body = json.loads(response["body"])
    assert response_body == [f'missing required header "{required_header}"']


def test_lambda_handler_returns_403_with_invalid_slack_signature_header():
    """Tests that invalid X-Slack-Signature headers cause HTTP 403."""
    bad_signature = "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd275196" \
                    "66489c69b503"

    request = make_request()
    request["headers"]["X-Slack-Signature"] = bad_signature

    response = lambda_handler(request)

    assert response["statusCode"] == 403
    response_body = json.loads(response["body"])
    assert response_body == ['X-Slack-Signature was invalid']


def test_lambda_handler_slack_authentication_example(monkeypatch):
    """Tests that the exact slack example returns a 200.

    https://api.slack.com/docs/verifying-requests-from-slack#step-by-step_walk-through_for_validating_a_request
    """
    monkeypatch.setattr(time, 'time', lambda: 1531420618)
    monkeypatch.setattr(os, 'environ',
                        {"SIGNING_SECRET": "8f742231b10e8888abcd99yyyzzz85a5"})

    headers = {
        "X-Slack-Signature": "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10b"
                             "d27519666489c69b503",
        "X-Slack-Request-Timestamp": "1531420618",
    }

    body = "token=xyzz0WbapA4vBCDEFasx0q6G&team_id=T1DC2JH3J&team_domain=tes" \
           "tteamnow&channel_id=G8PSS9T3V&channel_name=foobar&user_id=U2CERL" \
           "KJA&user_name=roadrunner&command=%2Fwebhook-collect&text=&respon" \
           "se_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT1DC2JH3J%2F39" \
           "7700885554%2F96rGlfmibIGlgcZRskXaIFfN&trigger_id=398738663015.47" \
           "445629121.803a0bc887a14d10d2c447fce8b6703c"
    print(body)

    request = {"body": body, "headers": headers}

    response = lambda_handler(request)
    assert response["statusCode"] == 200
