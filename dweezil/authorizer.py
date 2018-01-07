"""
dweezil.authorizer
~~~~~~~~~~~~~~~~~~~~~
Dweezil Authorizer Lambda
"""

import json
import logging

import credstash
from awacs.aws import Policy, Allow, Statement
from awacs.execute_api import Invoke

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def lambda_handler(event=None, _=None):
    if not event:
        unauthorized('event is null')

    bearer_token = event.get('authorizationToken', '')
    token = bearer_token[7:]  # strip 'Bearer '
    method_arn = event.get('methodArn', '')
    method_arn_parts = method_arn.split(':')
    if len(method_arn_parts) < 6:
        unauthorized(f"methodArn not valid: '{method_arn}'")
    region = method_arn_parts[3]
    acct_id = method_arn_parts[4]
    apig_parts = method_arn_parts[5].split('/')
    if len(apig_parts) < 2:
        unauthorized(f"methodArn not valid, apig invalid: '{method_arn}'")
    apig_id = apig_parts[0]
    stage = apig_parts[1]
    credstash_entry_name = 'dev' if stage.startswith('dev_') else stage
    try:
        secret = get_credstash_token(credstash_entry_name)
    except Exception:
        logger.error(f"Credstash token not found for arn '${method_arn}'")
        raise Exception('Unauthorized')

    if secret == token:
        logger.info('Authorization successful.')
        response = build_response(
            principal_id='dweezil-webhook',
            region=region,
            acct_id=acct_id,
            apig_id=apig_id,
            stage=stage
        )
        return response
    else:
        logger.error('Authorization has failed.')

    unauthorized('unknown')


def unauthorized(msg):
    logger.error(msg)
    raise Exception('Unauthorized')


def get_credstash_token(stage):
    credstash_key = 'dweezil-webhook-token-' + stage
    logger.info('Stage: ' + stage)
    logger.info('Checking token with credstash key: ' + credstash_key)
    return credstash.getSecret(credstash_key)


def build_response(*, principal_id, region, acct_id, apig_id, stage):
    resource_arn = \
        f'arn:aws:execute-api:{region}:{acct_id}:{apig_id}/{stage}/*/responses'
    policy = Policy(Version="2012-10-17",
                    Statement=[Statement(
                        Effect=Allow,
                        Action=[Invoke],
                        Resource=[resource_arn]
                    )]
                    )
    response = {'principalId': principal_id,
                'policyDocument': json.loads(policy.to_json())}
    return response
