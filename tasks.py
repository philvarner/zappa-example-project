import os
import re

from invoke import task

from dweezil.queue_forklift import create_or_update_queues
from dweezil.zappa_attach_policy import attach_policy_json
from dweezil.zappa_settings import generate_zappa_settings

QUEUE_NAME_PREFIX = 'Dweezil-InboundResponses'

ACCT_ID = 'acct_id'
REGION = 'region'
CS_KEY_ID = 'cs_key_id'  # credstash key ID

config = {
    'dev': {
        ACCT_ID: '209012249534',
        REGION: 'us-east-2',
        CS_KEY_ID: '316a2584-c9f3-4760-9d2d-779d5d650482'
    },
    'sandbox': {
        ACCT_ID: '812129021960',
        REGION: 'us-east-1',
        CS_KEY_ID: 'eb7a117b-a5dd-486d-897a-e2b0c98c7112',
    },
    'qa': {
        ACCT_ID: '812129021960',
        REGION: 'us-east-1',
        CS_KEY_ID: 'eb7a117b-a5dd-486d-897a-e2b0c98c7112',
    },
    'production': {
        ACCT_ID: '812129021960',
        REGION: 'us-east-1',
        CS_KEY_ID: 'eb7a117b-a5dd-486d-897a-e2b0c98c7112',
    }
}


@task
def tests(ctx, marker=None, open=False, stdout=False):
    marker_flag = f'-m {marker}' if marker else ''
    stdout_flag = '-s' if stdout else ''
    ctx.run(
        f'pytest {stdout_flag} --cov=dweezil'
        f' --cov-report html:tmp/cov_html'
        f' "{marker_flag}" tests',
        pty=True)
    if open:
        ctx.run('open tmp/cov_html/index.html')


@task
def create(ctx, env):
    create_queues_stack(ctx, env, resource_suffix(env))
    zappa(ctx, 'deploy', env, resource_suffix(env))
    certify(ctx, env)


@task
def certify(ctx, env):
    zappa(ctx, 'certify', env, resource_suffix(env))


@task
def delete(ctx, env):
    delete_queues_stack(ctx, resource_suffix(env))
    zappa(ctx, 'undeploy', env, resource_suffix(env))


@task
def update(ctx, env):
    create_queues_stack(ctx, env, resource_suffix(env))
    zappa(ctx, 'update', env, resource_suffix(env))


@task
def tail(ctx, env):
    zappa(ctx, 'tail', env, resource_suffix(env))


@task
def create_queues_stack(_ctx, env, resource_suffix):
    create_or_update_queues(
        region=config[env][REGION],
        resource_suffix=resource_suffix,
        queue_name_prefix=QUEUE_NAME_PREFIX
    )


@task
def delete_queues_stack(_ctx, env):
    pass


@task
def build_attach_policy(ctx, env, resource_suffix):
    output_filename = 'tmp/attach_policy.json'

    with open(output_filename, 'wt') as f:
        f.write(
            attach_policy_json(
                region=config[env][REGION],
                acct_id=config[env][ACCT_ID],
                key_id=config[env][CS_KEY_ID],
                queue_name=f'{QUEUE_NAME_PREFIX}-{resource_suffix}'
            )
        )

    print(f"Wrote {output_filename}")


@task
def build_zappa_settings(ctx, env, resource_suffix, username):
    output_filename = 'tmp/zappa_settings.yaml'

    with open(output_filename, 'wt') as f:
        f.write(
            generate_zappa_settings(
                template='settings/zappa_settings_template.yaml',
                resource_suffix=resource_suffix,
                region=config[env][REGION],
                queue_name_prefix=QUEUE_NAME_PREFIX,
                username=username
            )
        )

    print(f"Wrote {output_filename}")


def zappa(ctx, cmd, env, resource_suffix):
    build_attach_policy(ctx, env, resource_suffix)
    build_zappa_settings(ctx, env, resource_suffix, user())
    stage = f'dev_{user()}' if env == 'dev' else env
    zappa_cmd = f"zappa {cmd} {stage} -s tmp/zappa_settings.yaml"
    if cmd == 'certify' or cmd == 'undeploy':
        zappa_cmd += ' --yes'
    ctx.run(zappa_cmd, pty=True)


def user():
    return re.sub('\.', '', os.environ.get('USER'))


def resource_suffix(env):
    return f'dev-{user()}' if env == 'dev' else env
