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
from complaint_counter.authentication import ForbiddenException


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


@pytest.fixture
def auth_check():
    """Mock out and return an auth check to be injected into lambda_handler."""
    auth_check = Mock()
    auth_check.return_value = None  # by default, do nothing
    return auth_check


def test_lambda_handler_returns_200(auth_check):
    """Test that lambda_handler returns a 200 status code."""
    request = make_request()
    response = lambda_handler(request, authentication_check=auth_check)
    assert response['statusCode'] == 200


def test_lambda_handler_quotes_the_complaint(auth_check):
    """Test that the lambda_handler returns the complaint as a quote."""
    complaint = "about foo and bar"

    request_body = {"text": complaint}
    request = make_request(request_body)

    response = lambda_handler(request, authentication_check=auth_check)

    assert f'\n> {complaint}' in json.loads(response['body'])['text']


def test_lambda_handler_saves_complaints_to_storage(dynamodb, auth_check):
    """Tests that lambda_handler saves complaints."""
    text = "dynamo db serializes objects"
    username = "johnquincyadams"

    body = {"text": text, "user_name": username}
    request = make_request(body)

    lambda_handler(request, authentication_check=auth_check)

    assert len(dynamodb.put_item.mock_calls) == 1
    args, kwargs = dynamodb.put_item.call_args

    item = kwargs["Item"]
    assert item["uuid"]["S"]
    assert item["timestamp"]["N"]
    assert item["reporter"]["S"] == username
    assert item["complaint"]["S"] == text


def test_lambda_handler_returns_a_total_number_of_complaints(dynamodb,
                                                             auth_check):
    """Tests that lambda_handler is counting the complaints."""
    count = 774
    dynamodb.scan.return_value = {"Count": 774}

    request = make_request()
    response = lambda_handler(request, authentication_check=auth_check)

    response_text = json.loads(response['body'])['text']
    assert f"\nCurtis has *{count}* recorded complaints." in response_text


def test_lambda_handler_returns_a_channel_visible_response(auth_check):
    """Tests that lambda_handler yells curtis's complaints to the channel."""
    request = make_request()
    response = lambda_handler(request, authentication_check=auth_check)

    assert json.loads(response['body'])['response_type'] == 'in_channel'


def test_lambda_handler_converts_auth_check_fail_to_403(auth_check):
    """Tests that lambda_handler returns 403 on auth_check failures."""
    request = make_request()
    auth_check.side_effect = ForbiddenException("failed authentication")

    response = lambda_handler(request, authentication_check=auth_check)

    assert response["statusCode"] == 403
    assert json.loads(response["body"]) == ["failed authentication"]


def test_lambda_handler_calls_auth_check_with_request(auth_check):
    """Test that lambda_handler calls authentication_check with request."""
    request = make_request()

    lambda_handler(request, authentication_check=auth_check)

    auth_check.assert_called_with(request)
