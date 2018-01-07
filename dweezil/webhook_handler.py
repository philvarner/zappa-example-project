"""
dweezil.webhook_handler
~~~~~~~~~~~~~~~~~~~~~
Dweezil Webhook Handler Lambda
"""

import json
import logging
import os

import boto3
import falcon
from botocore.exceptions import ClientError
from falcon import HTTP_200, HTTP_400, HTTP_500

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ResponseResource:
    def on_post(self, req, resp):
        logger.info('Lambda function invoked')

        queue_name = os.getenv('QUEUE_NAME')
        if queue_name is None:
            resp.status = HTTP_500
            resp.media = json.dumps({'error': 'QUEUE_NAME not set'})
            return

        param1 = req.get_param('param1', None)

        if not param1:
            resp.status = HTTP_400
            resp.media = json.dumps({'error': 'param1 not sent'})
            return

        msg_dict = {"param1": param1}
        msg_json = json.dumps(msg_dict)

        logger.info(f'sending msg >>{msg_json}<< to queue "{queue_name}"')

        try:
            response = boto3.resource('sqs') \
                .get_queue_by_name(QueueName=queue_name) \
                .send_message(MessageBody=msg_json)
        except ClientError as e:
            logger.error(f'Error calling SQS: {str(e)}')
            resp.status = HTTP_500
            resp.media = f'Error enqueuing response'
            return

        msg_dict['sqs_msg_id'] = response.get("MessageId", 'empty')
        msg_json = json.dumps(msg_dict)

        logger.info(f'sent msg {msg_json}')

        resp.status = HTTP_200
        resp.media = msg_json


app = api = falcon.API()
api.add_route('/responses', ResponseResource())
