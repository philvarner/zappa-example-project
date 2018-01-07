import json
from datetime import datetime

import boto3
import cfn_flip
from awacs.aws import Statement, AWSPrincipal, Policy, Allow
from awacs.kms import Action as KmsAction
from botocore.exceptions import ClientError
from troposphere import GetAtt, Output, Name, Ref, Template, \
    Sub, Export
from troposphere.kms import Key, Alias
from troposphere.sqs import Queue, RedrivePolicy

USER = 'arn:aws:iam::${AWS::AccountId}:user'

All = '*'
AllResources = ['*']


# noinspection PyPep8Naming
def generate_queues_template(QueueNamePrefix, Environment):
    QueueName = f'{QueueNamePrefix}-{Environment}'
    DLQQueueName = f'{QueueNamePrefix}DLQ-{Environment}'

    t = Template(
        Description='A template for a messaging queue')
    t.version = '2010-09-09'

    KMSKey = t.add_resource(
        Key(
            'KMSKey',
            Description=f'KMS Key for encrypting {QueueName}',
            Enabled=True,
            EnableKeyRotation=True,
            KeyPolicy=Policy(
                Version='2012-10-17',
                Statement=[
                    Statement(
                        Sid='Enable IAM User Permissions',
                        Effect=Allow,
                        Principal=AWSPrincipal(
                            Sub('arn:aws:iam::${AWS::AccountId}:root')),
                        Action=[KmsAction(All)],
                        Resource=AllResources
                    ),
                    Statement(
                        Sid='Allow access for Key Administrators',
                        Effect=Allow,
                        Principal=AWSPrincipal(
                            [
                                Sub(f'{USER}/frank'),
                                Sub(f'{USER}/moonunit')
                            ]
                        ),
                        Action=[
                            KmsAction('Create*'),
                            KmsAction('Describe*'),
                            KmsAction('Enable*'),
                            KmsAction('List*'),
                            KmsAction('Put*'),
                            KmsAction('Update*'),
                            KmsAction('Revoke*'),
                            KmsAction('Disable*'),
                            KmsAction('Get*'),
                            KmsAction('Delete*'),
                            KmsAction('ScheduleKeyDeletion'),
                            KmsAction('CancelKeyDeletion')
                        ],
                        Resource=AllResources
                    )
                ]
            )
        )
    )

    t.add_resource(
        Alias(
            'KMSKeyAlias',
            AliasName=f'alias/{QueueName}',
            TargetKeyId=Ref(KMSKey)
        )
    )

    dlq = t.add_resource(
        Queue(
            'DeadLetterQueue',
            QueueName=DLQQueueName,
            MaximumMessageSize=262144,  # 256KiB
            MessageRetentionPeriod=1209600,  # 14 days
            VisibilityTimeout=30
        )
    )

    t.add_resource(
        Queue(
            'PrimaryQueue',
            QueueName=QueueName,
            MaximumMessageSize=262144,  # 256KiB
            MessageRetentionPeriod=1209600,  # 14 days
            VisibilityTimeout=30,
            RedrivePolicy=RedrivePolicy(
                deadLetterTargetArn=GetAtt(
                    dlq.title,
                    'Arn'),
                maxReceiveCount=10
            ),
            KmsMasterKeyId=Ref(KMSKey),
            KmsDataKeyReusePeriodSeconds=300
        )
    )

    t.add_output([
        Output(
            'QueueArn',
            Description=f'ARN of {QueueName} Queue',
            Value=GetAtt('PrimaryQueue', 'Arn'),
            Export=Export(Name(Sub('${AWS::StackName}:PrimaryQueueArn')))
        ),
        Output(
            'KmsKeyArn',
            Description=f'KMS Key ARN for {QueueName} Queue',
            Value=GetAtt('KMSKey', 'Arn'),
            Export=Export(Name(Sub('${AWS::StackName}:KmsKeyArn')))
        )
    ])

    return t


def stack_exists(client, stack_name):
    stacks = client.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack['StackStatus'] == 'DELETE_COMPLETE':
            continue
        if stack_name == stack['StackName']:
            return True
    return False


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def create_or_update_queues(*, region, resource_suffix, queue_name_prefix):
    template_yaml = cfn_flip.to_yaml(
        generate_queues_template(queue_name_prefix, resource_suffix).to_json()
    )

    client = boto3.client('cloudformation', region_name=region)
    stack_name = f'dweezil-queues-{resource_suffix}'
    params = {
        'StackName': stack_name,
        'TemplateBody': template_yaml
    }

    try:
        if stack_exists(client, stack_name):
            print(f'Updating stack {stack_name}...', end='', flush=True)
            stack_result = client.update_stack(**params)
            waiter = client.get_waiter('stack_update_complete')
        else:
            print(f'Requesting "{stack_name}" stack creation... ',
                  end='', flush=True)
            stack_result = client.create_stack(**params)
            waiter = client.get_waiter('stack_create_complete')
        print(f'waiting for complete... ', end='', flush=True)
        waiter.config.delay = 15
        waiter.config.max_attempts = 20
        waiter.wait(StackName=stack_name)
    except ClientError as ex:
        error_message = ex.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print(' no changes.')
        else:
            raise
    else:
        print(' finished.')
        print('Stack output:')
        print(json.dumps(
            client.describe_stacks(StackName=stack_result['StackId']),
            indent=2,
            default=json_serial
        ))
