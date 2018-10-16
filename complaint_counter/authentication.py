"""Authentication checks for Lambda API gateway requests."""
from hashlib import sha256
import hmac


class ForbiddenException(Exception):
    """Request being processed fails Authorization."""


class SlackAuthenticationCheck(object):
    """Check requests against a Slack Signing Secret.

    For details see:
    https://api.slack.com/docs/verifying-requests-from-slack
    """

    required_headers = ("X-Slack-Request-Timestamp", "X-Slack-Signature")

    def __init__(self, signing_secret, version="v0"):
        """Instantiate with the Signing Secret provided by the Slack App."""
        self.secret = signing_secret
        self.version = version

    def __call__(self, request):
        """Raise an exception if request is unauthorized."""
        headers = request.get("headers", dict())

        for required_header in self.required_headers:
            if required_header not in headers:
                message = f'missing required header "{required_header}"'
                raise ForbiddenException(message)

        timestamp = int(headers["X-Slack-Request-Timestamp"])

        # TODO Check X-Slack-Request-Timestamp vs Current Time

        raw_signature = f"{self.version}:{timestamp}:{request['body']}"
        signature_hmac = hmac.new(self.secret.encode(), raw_signature.encode(),
                                  sha256)
        signature = f"{self.version}={signature_hmac.hexdigest()}".encode()

        encoded_header = headers["X-Slack-Signature"].encode()

        if not hmac.compare_digest(signature, encoded_header):
            raise ForbiddenException("X-Slack-Signature was invalid")
