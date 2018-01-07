from itertools import chain

from awacs.aws import Policy, Allow, Statement
from awacs.awslambda import InvokeFunction
from awacs.dynamodb import GetItem as DdbGetItem, Query as DdbQuery, \
    Scan as DdbScan
from awacs.ec2 import *
from awacs.kms import Decrypt, Action as KMSAction
from awacs.logs import CreateLogGroup, PutLogEvents, CreateLogStream
from awacs.route53 import Action as Route53Action
from awacs.sqs import Action as SqsAction, GetQueueUrl
from awacs.xray import PutTraceSegments, PutTelemetryRecords

All = "*"
AllResources = ["*"]


def attach_policy_json(**kwargs):
    return attach_policy(**kwargs).to_json()


def attach_policy(*, region, acct_id, key_id, queue_name):
    return Policy(
        Version='2012-10-17',
        Statement=list(chain.from_iterable([
            stmts_logging(region, acct_id),
            stmts_lambda_invocation(),
            stmts_custom_domain(),
            stmts_vpc(),
            stmts_custom_authorizer(region, acct_id, key_id),
            stmts_app_webhook_handler(region, acct_id, queue_name),
        ]))
    )


def stmts_logging(region, acct_id):
    return [Statement(
        Effect=Allow,
        Action=[CreateLogGroup],
        Resource=[f'arn:aws:logs:{region}:{acct_id}:*']),
        Statement(
            Effect=Allow,
            Action=[CreateLogStream, PutLogEvents],
            Resource=[f'arn:aws:logs:{region}:{acct_id}:*']
            # Resource=[f'arn:aws:logs:{region}:{acct_id}:log-group:/aws/lambda/pvarner-test-1:*'
        ), Statement(
            Effect=Allow,
            Action=[PutTraceSegments, PutTelemetryRecords],
            Resource=AllResources
        )]


def stmts_lambda_invocation():
    return [Statement(
        Effect=Allow,
        Action=[InvokeFunction],
        Resource=AllResources  # TODO: my name
    )]


def stmts_custom_domain():
    return [Statement(
        Effect=Allow,
        Action=[Route53Action(All)],
        Resource=AllResources  # TODO: restrict to my domain?
    )]


def stmts_vpc():
    return [Statement(
        Effect=Allow,
        Action=[
            AttachNetworkInterface,
            CreateNetworkInterface,
            DeleteNetworkInterface,
            DescribeInstances,
            DescribeNetworkInterfaces,
            DetachNetworkInterface,
            ModifyNetworkInterfaceAttribute,
            ResetNetworkInterfaceAttribute
        ],
        Resource=AllResources)]


def stmts_app_webhook_handler(region, acct_id, queue_name):
    return [
        Statement(
            Effect=Allow,
            Action=[GetQueueUrl],
            Resource=[f"arn:aws:sqs:{region}:{acct_id}:*"]
        ),
        Statement(
            Effect=Allow,
            Action=[SqsAction(All)],
            Resource=[f"arn:aws:sqs:{region}:{acct_id}:*"]  # TODO: WRONG
        ),
        Statement(
            Effect=Allow,
            Action=[KMSAction(All)],
            Resource=[f"arn:aws:kms:{region}:{acct_id}:*"]  # TODO: WRONG
        )
    ]


def stmts_custom_authorizer(region, acct_id, key_id):
    return [
        # credstash
        Statement(
            Effect=Allow,
            Action=[Decrypt],
            Resource=[
                f'arn:aws:kms:{region}:{acct_id}:key/{key_id}']
        ),
        # credstash
        Statement(
            Effect=Allow,
            Action=[DdbGetItem, DdbQuery, DdbScan],
            Resource=[
                f'arn:aws:dynamodb:{region}:{acct_id}:table/credential-store'
            ]
        )
    ]
