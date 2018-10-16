"""Tests for complaint_counter.authentication.

Tests in here are built using the example from the slack API documentation:

    https://api.slack.com/docs/verifying-requests-from-slack#step-by-step_walk-through_for_validating_a_request
"""
import time

import pytest

from complaint_counter import authentication


@pytest.fixture
def signing_secret():
    """Slack signing secret for the request."""
    return "8f742231b10e8888abcd99yyyzzz85a5"


@pytest.fixture()
def timestamp(monkeypatch):
    """Timestamp associated with the request & adds latency to time.time()."""
    current_time = 1531420618
    monkeypatch.setattr(time, 'time', lambda: current_time + 1)
    return current_time


@pytest.fixture()
def request_dict(signing_secret, timestamp):
    """Return request associated with slack authentication example."""
    headers = {
        "X-Slack-Signature": "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10b"
                             "d27519666489c69b503",
        "X-Slack-Request-Timestamp": str(timestamp),
    }

    body = "token=xyzz0WbapA4vBCDEFasx0q6G&team_id=T1DC2JH3J&team_domain=tes" \
           "tteamnow&channel_id=G8PSS9T3V&channel_name=foobar&user_id=U2CERL" \
           "KJA&user_name=roadrunner&command=%2Fwebhook-collect&text=&respon" \
           "se_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT1DC2JH3J%2F39" \
           "7700885554%2F96rGlfmibIGlgcZRskXaIFfN&trigger_id=398738663015.47" \
           "445629121.803a0bc887a14d10d2c447fce8b6703c"

    return {"body": body, "headers": headers}


def test_lambda_handler_slack_authentication_example(signing_secret,
                                                     request_dict):
    """Tests that the exact slack example returns a 200."""
    check = authentication.SlackAuthenticationCheck(signing_secret)

    try:
        check(request_dict)
    except authentication.ForbiddenException:
        pytest.fail("Request failed authentication but should have passed.")


# TODO Move authentication related tests here and just make sure the
# lambda-handler calls authentication check


@pytest.mark.parametrize("body,headers", (
    ("text=helloworld", None),
    (None, {"X-Slack-Signature": "v0=ac86bcd8b786a8b0871323abcbade312f13ad"}),
    (None, {"X-Slack-Request-Timestamp": "1531421001"}),
))
def test_lambda_handler_slack_authentication_fails(
    signing_secret,
    request_dict,
    body,
    headers,
):
    """Tests that headers with mismatching bodies raise ForbiddenException."""
    check = authentication.SlackAuthenticationCheck(signing_secret)

    if body is not None:
        request_dict["body"] = body

    if headers is not None:
        request_dict["headers"].update(headers)

    with pytest.raises(authentication.ForbiddenException):
        check(request_dict)
