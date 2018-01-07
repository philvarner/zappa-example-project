#!/usr/bin/env groovy

// pipeline for Dweezil webhook handler

pipeline {

    agent any

    parameters {
        string(name: 'AWS_REGION', defaultValue: 'us-east-1', description: 'AWS Region to deploy to')
        string(name: 'COMMAND', defaultValue: 'update', description: 'Deployment command to run (create or update)')
        string(name: 'DEPLOY_ENV', defaultValue: '', description: 'environment to deploy to')
    }

    stages {
        stage('Deploy') {
            steps {
                echo "Deploying '${BRANCH_NAME}', deploy env set to '${DEPLOY_ENV}'..."
                script {
                    def branch_to_env_mapping = [master: 'qa', production: 'production']
                    if (DEPLOY_ENV == '') {
                        DEPLOY_ENV = branch_to_env_mapping[BRANCH_NAME]
                        if (DEPLOY_ENV == null) DEPLOY_ENV = 'sandbox'
                    }
                }
                echo "Deploying branch '${BRANCH_NAME}' to deploy env '${DEPLOY_ENV}'..."
                sh """
                    source scripts/jenkins_python_setup.sh
                    export AWS_REGION=${AWS_REGION}
                    invoke ${COMMAND} --env ${DEPLOY_ENV}
                """
            }
        }
    }
}
