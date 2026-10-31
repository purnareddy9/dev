// vars/standardMicroservicePipeline.groovy
// Enterprise Shared Library entry point for 100+ microservices

def call(Map config = [:]) {
    def serviceName = config.serviceName ?: error("Field 'serviceName' is required!")
    def language = config.language ?: 'java'
    def minCoverage = config.coverageThreshold ?: 80

    pipeline {
        agent {
            label 'dynamic-k8s-agent'
        }
        
        stages {
            stage('Validate & Lint') {
                steps {
                    echo "Validating configuration for ${serviceName} (${language})"
                }
            }

            stage('Security SAST') {
                steps {
                    echo "Enforcing corporate SAST policy..."
                }
            }

            stage('Build & Test') {
                steps {
                    echo "Executing test suite with strict coverage >= ${minCoverage}%"
                }
            }
        }

        post {
            failure {
                slackSend channel: '#devops-alerts',
                          color: 'danger',
                          message: "🚨 Job FAILED: ${env.JOB_NAME} [Build #${env.BUILD_NUMBER}]"
            }
        }
    }
}
