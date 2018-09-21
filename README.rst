Curtis Complaint Counter
========================

This is a slack integration to track Curtis La Graff's complaints.

Development Quickstart
----------------------

#. Create a virtual environment

#. Run ``setup.py develop``

   ::

     python setup.py develop

Deployment
----------

After installing via ``setup.py`` run the following:

::

  $ deploy

This will update the Lambda endpoint that the API Gateway routes Slack-integration's requests to.


Infrastructure
==============

* `Curtis Complaint Counter's API Gateway <https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis/seh9do9685/resources/ghxnuw26v1>`__
* `Curtis Complaint Counter's Lambda Endpoint <https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/CurtisComplaintCounter?tab=graph>`__
* `Curtis Complaint Counter's DynamoDB table <https://console.aws.amazon.com/dynamodb/home?region=us-east-1#tables:selected=CurtisComplaints;tab=items>`__
