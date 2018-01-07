An example project using Zappa, Invoke, and Troposphere

===========

# Overview

Components in this repo:
1. Zappa project that deploys an API Gateway and Lambda for accepting webhook calls and enqueuing on SQS
1. S3 event listener

The repo consists of:
1. Multibranch declarative pipline Jenkinsfile for CI build
1. Invoke library build definitions for deploying CloudFormation templates and Zappa project
1. Generator for Zappa execution IAM Policy
1. Generator for Zappa config file
1. Troposphere code to create AWS Resources not defined in Zappa configuration
1. API Gateway Custom Authorizer using Credstash

In this project,
* `dweezil` is used as the example application and package name
* `rcollimore` is used as the example username

Most of the configuration for deploying to AWS is generated from templates to allow multiple developers to deploy to
the same AWS account without stepping on each other's resources, so elements are usually suffixed with a unique name,
e.g., 'dev-rcollimore'.

[Credstash](https://github.com/fugue/credstash) is used for storing the (single) secret token validated by the
custom authorizer.

#  Setting up a dev environment

## Dependencies

* Python or [pyenv](https://github.com/pyenv/pyenv) 3.6 to bootstrap pipenv

## Install pipenv

```bash
pip3 install pipenv
```

## Setting up a pipenv virtualenv

From within this repo, run:

```bash
pipenv install --dev
```

## Running the linter

```bash
pipenv run pycodestyle .
```

## Running the tests

```bash
pipenv run pytest tests
```

# Webhook Handler API Gateway + Lambda

* [Falcon](https://falconframework.org/) web service framework w/ WSGI interface
* [Zappa](https://github.com/Miserlou/Zappa) serverless Python framework

All of these commands need to be run in the context of `pipenv shell` or executed with `pipenv run` prefixed.

## Execution

### Run the web service locally with Gunicorn

```
QUEUE_NAME=Dweezil-InboundResponses-dev-$USER gunicorn dweezil.webhook_handler:app
```

### Initially deploy environment 'dev' to AWS

```bash
invoke create --env dev
```

### Initially setup SSL certs for environment 'dev' in AWS

```bash
invoke certify --env dev
```

### Update existing environment 'dev' to AWS

```bash
invoke update --env dev
```

Invoke via API Gateway endpoint:

Without a Custom Domain Name configured and with the custom authorizer turned off:
```bash
curl -v -X POST 'https://qm8sarlacc.execute-api.us-east-1.amazonaws.com/dev_pvarner/responses?param1=foo' ; echo '\n'
```
note that the url is of the form https://{host}/{api gateway stage}/{wsgi app resource}

With a Custom Domain Name configured:
```bash
curl -v -X POST 'https://webhook.example.org/responses?answer=foo' -H 'Authorization: Bearer 1234' && echo
```

Creating a new Custom Domain Name:
* API Gateway -> Custom Domain Names -> (Create Custom Domain Name)
* Domain Name: e.g., dweezil-dev-rcollimore.example.org
* Edge Optimized (as the certificate lives in us-east-1, it has to be)
* ACM Certificate: *.example.org, the only one
* Base Path Mappings
  * Path: (blank)
  * Destination: <your api gateway>
  * unnamed field: dev
* Save
Then wait for ~40 minutes (not joke) -- it takes that long for all the things to propagate.

Create a Route53 A record to your custom domain
* Edit Hosted Zone '.example.org'
* Name: dweezil-dev-rcollimore
* Type: A
* Alias: Yes
  * Alias Target: CloudFront host, e.g., dwdl1utqpi3k6.cloudfront.net. from your Custom Domain Name
* Routing Policy: Simple

Debug:
```bash
invoke tail --env dev
```

## Custom Authorizer

TODO: Write something about this.
