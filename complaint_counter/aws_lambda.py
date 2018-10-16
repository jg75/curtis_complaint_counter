"""An AWS Lambda endpoint expecting Slack integration requests."""
import json
import os
import time
import urllib.parse
import uuid

from boto3 import client

from .authentication import SlackAuthenticationCheck, ForbiddenException


dynamodb = client('dynamodb')


SIGNING_SECRET = os.environ.get('SIGNING_SECRET')
authentication_check = SlackAuthenticationCheck(SIGNING_SECRET)


def lambda_handler(event, context=None, *,
                   authentication_check=authentication_check):
    """Lamdba endpoint to count curtis's complaints."""
    try:
        authentication_check(event)
    except ForbiddenException as auth_error:
        return {
            "statusCode": 403,
            "headers": dict(),
            "body": json.dumps(auth_error.args)
        }

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
