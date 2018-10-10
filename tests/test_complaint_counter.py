"""Tests for complaint_counter.py"""
import json
from unittest.mock import MagicMock, Mock
from urllib.parse import urlencode

import pytest

import complaint_counter
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


@pytest.fixture(autouse=True)
def dynamodb(monkeypatch):
    """Mock away the dynamodb client used by lambda_handler."""
    # boto3 is not installed for testing
    monkeypatch.setattr(complaint_counter, 'boto3', Mock(), raising=False)

    dynamodb = MagicMock()
    monkeypatch.setattr(complaint_counter, 'dynamodb', dynamodb)
    return dynamodb


def test_lambda_handler_returns_200():
    """Test that lambda_handler returns a 200 status code."""
    response = lambda_handler({'body': request_body()})
    assert response['statusCode'] == 200


def test_lambda_handler_quotes_the_complaint():
    """Test that the lambda_handler returns the complaint as a quote."""
    complaint = "about foo and bar"
    response = lambda_handler({"body": request_body(text=complaint)})

    assert f'\n> {complaint}' in json.loads(response['body'])['text']


def test_lambda_handler_saves_complaints_to_storage(dynamodb):
    """Tests that lambda_handler saves complaints."""
    text = "dynamo db serializes objects"
    username = "johnquincyadams"
    # uuid = some_uuid
    # timestamp = epoch

    body = request_body(text=text, user_name=username)
    lambda_handler({"body": body})

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

    response = lambda_handler({"body": request_body()})

    response_text = json.loads(response['body'])['text']
    assert f"\nCurtis has *{count}* recorded complaints." in response_text


def test_lambda_handler_returns_a_channel_visible_response():
    """Tests that lambda_handler yells curtis's complaints to the channel."""
    response = lambda_handler({"body": request_body()})

    assert json.loads(response['body'])['response_type'] == 'in_channel'
