"""Tests for complaint_counter.py."""
import json
from unittest.mock import MagicMock, Mock
from urllib.parse import urlencode

import pytest

import complaint_counter.aws_lambda
from complaint_counter import lambda_handler


def request_body(**kwargs):
    """Create a QS request body, like one provided from a slack request."""
    kwargs.setdefault("token", "ftMJyTJlA4qo8QNY3PVhuYf6")
    kwargs.setdefault("team_id", "T18UTUL93")
    kwargs.setdefault("team_domain", "disjointedimages")
    kwargs.setdefault("channel_id", "D81P2TLNM")
    kwargs.setdefault("channel_name", "directmessage")
    kwargs.setdefault("user_id", "U81JYT64Q")
    kwargs.setdefault("user_name", "maxwellgbrown")
    kwargs.setdefault("command", "/curtis_complained")
    kwargs.setdefault("text", "")
    kwargs.setdefault(
        "response_url",
        "https://hooks.slack.com/commands/T18UTUL93/440741347573"
        "/RSYHp7T18s0uP4eU7hGFdSm6",
    )

    return urlencode(kwargs)


def request_headers(**kwargs):
    """Return request headers expected from a typical slack request.

    These values were taken directly from the Slack documentation example.
    https://api.slack.com/docs/verifying-requests-from-slack#step-by-step_walk-through_for_validating_a_request
    """
    kwargs.setdefault(
        "X-Slack-Signature",
        "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503",
    )
    kwargs.setdefault("X-Slack-Request-Timestamp", "1531420618")
    return kwargs


@pytest.fixture(autouse=True)
def dynamodb(monkeypatch):
    """Mock away the dynamodb client used by lambda_handler."""
    # boto3 is not installed for testing
    monkeypatch.setattr(complaint_counter.aws_lambda, 'boto3', Mock(),
                        raising=False)

    dynamodb = MagicMock()
    monkeypatch.setattr(complaint_counter.aws_lambda, 'dynamodb', dynamodb)
    return dynamodb


def test_lambda_handler_returns_200():
    """Test that lambda_handler returns a 200 status code."""
    request = {'body': request_body(), 'headers': request_headers()}
    response = lambda_handler(request)
    assert response['statusCode'] == 200


def test_lambda_handler_quotes_the_complaint():
    """Test that the lambda_handler returns the complaint as a quote."""
    complaint = "about foo and bar"
    request = {"body": request_body(text=complaint),
               "headers": request_headers()}
    response = lambda_handler(request)

    assert f'\n> {complaint}' in json.loads(response['body'])['text']


def test_lambda_handler_saves_complaints_to_storage(dynamodb):
    """Tests that lambda_handler saves complaints."""
    text = "dynamo db serializes objects"
    username = "johnquincyadams"
    # uuid = some_uuid
    # timestamp = epoch

    request = {"body": request_body(text=text, user_name=username),
               "headers": request_headers()}
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

    request = {"body": request_body(), "headers": request_headers()}
    response = lambda_handler(request)

    response_text = json.loads(response['body'])['text']
    assert f"\nCurtis has *{count}* recorded complaints." in response_text


def test_lambda_handler_returns_a_channel_visible_response():
    """Tests that lambda_handler yells curtis's complaints to the channel."""
    request = {"body": request_body(), "headers": request_headers()}
    response = lambda_handler(request)

    assert json.loads(response['body'])['response_type'] == 'in_channel'


def test_lambda_handler_returns_403_with_no_slack_signature_header():
    """Tests that missing X-Slack-Signature headers cause HTTP 403."""
    headers = request_headers()
    headers.pop("X-Slack-Signature")

    request = {"body": request_body(), "headers": headers}
    response = lambda_handler(request)

    assert response["statusCode"] == 403


def test_lambda_handler_returns_403_with_no_slack_request_timestamp_header():
    """Tests that missing X-Slack-Request-Timestamp causes HTTP 403."""
    headers = request_headers()
    headers.pop("X-Slack-Request-Timestamp")

    request = {"body": request_body(), "headers": headers}
    response = lambda_handler(request)

    assert response["statusCode"] == 403
