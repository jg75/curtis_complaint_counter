"""An AWS Lambda endpoint expecting Slack integration requests."""
from hashlib import sha256
import hmac
import json
import os
import time
import urllib.parse
import uuid

from boto3 import client


dynamodb = client('dynamodb')


class ForbiddenException(Exception):
    """Request being processed fails Authorization."""

    def as_response(self):
        """Return a valid Lambda-API Gateway integration response."""
        return {
            "statusCode": 403,
            "headers": dict(),
            "body": json.dumps(self.args),
        }


def _authentication_check(request):
    # https://api.slack.com/docs/verifying-requests-from-slack#step-by-step_walk-through_for_validating_a_request
    headers = request.get("headers", dict())

    for required_header in ("X-Slack-Request-Timestamp", "X-Slack-Signature"):
        if required_header not in headers:
            message = f'missing required header "{required_header}"'
            raise ForbiddenException(message)

    secret = os.environ["SIGNING_SECRET"]
    timestamp = int(headers["X-Slack-Request-Timestamp"])

    # TODO Check X-Slack-Request-Timestamp vs Current Time

    raw_signature = f"v0:{timestamp}:{request['body']}"
    signature_hmac = hmac.new(secret.encode(), raw_signature.encode(), sha256)
    signature = b"v0=" + signature_hmac.hexdigest().encode()

    encoded_header = headers["X-Slack-Signature"].encode()

    if not hmac.compare_digest(signature, encoded_header):
        raise ForbiddenException("X-Slack-Signature was invalid")


def lambda_handler(event, context=None):
    """Lamdba endpoint to count curtis's complaints."""
    try:
        _authentication_check(event)
    except ForbiddenException as auth_error:
        return auth_error.as_response()

    parsed_body = urllib.parse.parse_qs(event["body"])
    # query strings can be multiple; just take the first of each found
    request_body = {k: v[0] for k, v in parsed_body.items()}

    command_text = request_body.get('text', '')

    # Store complaint in data store
    dynamodb.put_item(
        TableName="CurtisComplaints",
        Item={
            "uuid": {"S": str(uuid.uuid4())},
            "timestamp": {"N": f"{time.time():.10g}"},
            "complaint": {"S": command_text},
            "reporter": {"S": request_body['user_name']},
        }
    )

    response_body = f'*Curtis Complained!*\n\n> {command_text}'

    # NOTE: scanning a dynamo table can be a really expensive operation, but
    #       it's the only way to get a live count of records in the table.
    #       Since this table will likely only be very small it will likely be
    #       okay for the forseeable future.
    scan = dynamodb.scan(TableName="CurtisComplaints")
    response_body += f'\n\nCurtis has *{scan["Count"]}* recorded complaints.'

    response = {
        'statusCode': 200,
        'headers': dict(),
        'body': json.dumps({
            'response_type': 'in_channel',
            'text': response_body,
        }),
    }
    return response
