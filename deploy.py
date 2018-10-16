"""Deployment script for the Curtis Complaint Counter."""
import io
import os
import zipfile

from boto3 import client


def main():
    """Deploy the curtis complaint lambda.

    This will only publish a new version. It will NOT tag that version so that
    the API Gateway will communicate with it.
    """
    aws_lambda = client('lambda')

    code_zip = io.BytesIO()

    with zipfile.ZipFile(code_zip, 'w') as archive:
        for root, dirs, files in os.walk('complaint_counter'):
            for filename in (f for f in files if not f.endswith(".pyc")):
                filepath = os.path.join(root, filename)
                archive.write(filepath)

    aws_lambda.update_function_code(
        FunctionName="CurtisComplaintCounter",
        ZipFile=code_zip.getvalue(),
        Publish=True
    )


if __name__ == '__main__':
    main()
