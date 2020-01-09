pipeline {
    //-- Run on any available worker (agent) --\\
    agent any
    environment {
    //-- Read the worker version number
    WORKER_VERSION = readFile "${env.WORKSPACE}/version.txt"

    //-- Remove '/' character from the git branch name if it is present
    //-- Important note: Jenkins configuration must include 'Check out to matching local branch'
    WORKER_BRANCH = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD | tr / -').trim()

    //-- Reference the docker hub repo for the worker
    WORKER_REPO = "usgseros/espa-worker"

    //-- GIT SHORT HASH for latest commit
    GIT_SHORT_HASH = sh(returnStdout: true, script: "git log -n 1 --pretty=format:'%h'").trim()
    }

    //-- Job Stages (Actions) --\\
    stages {

        stage('Build') {
            steps {
                echo 'Build steps here.'

                echo "Worker version ${env.WORKER_VERSION}"
                echo "Current worker branch ${env.WORKER_BRANCH}"
                echo "Worker repo is referenced as ${env.WORKER_REPO}"
                echo "Last commit ${env.GIT_SHORT_HASH}"

                // Update workspace timestamp to prevent nightly cleanup script from removing workspace during a job run
                sh script: """
                    touch "${env.WORKSPACE}"
                """, label: "Update workspace timestamp - prevents workspace cleanup during job run"

                echo 'Building Docker Image from Dockerfile in project.'

                script {
                    //-- Build the image no matter which branch we are on
                    def customImage = docker.build("--no-cache", "${WORKER_REPO}:${WORKER_BRANCH}-${WORKER_VERSION}-${GIT_SHORT_HASH}", ".")
                    echo "Docker image id in same script block is: ${customImage.id}"

                    // Make image object available to later stages
                    CUSTOM_IMAGE = customImage
                }
            }
        }

        stage('Test') {
            steps {
                echo 'Testing steps here.'
                echo "Docker image id in this stage is: ${CUSTOM_IMAGE.id}"

                script {
                    // Test commands inside of the built image
                    CUSTOM_IMAGE.inside {
                        // Show python version inside of container
                        sh 'python -V'
                        // List installed pip packages inside container
                        sh 'pip list'

                        sh 'nose2 --fail-fast --with-coverage'
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploy steps here.'
                echo 'Push image to docker hub registry'
                script {
                    // Only push to docker hub for develop and master branches
                    if (WORKER_BRANCH == 'master') {
                        // Specify the Dockerhub registry and Jenkins stored credentials
                        docker.withRegistry('https://index.docker.io/v1/', 'espa-docker-hub-credentials') {
                            // Push previously built image to registry
                            CUSTOM_IMAGE.push()
                        }
                    }
                    if (WORKER_BRANCH == 'develop') {
                        // Specify the Dockerhub registry and Jenkins stored credentials
                        docker.withRegistry('https://index.docker.io/v1/', 'espa-docker-hub-credentials') {
                            // Push previously built image to registry
                            CUSTOM_IMAGE.push()
                        }
                    } else {
                    echo "Not publishing image for branch ${env.BRANCH_NAME}"
                    }
                }
            }
        }

    }

    //-- Run After Job Stages Are Complete --\\
    post {
        always {
            echo 'Pipeline Complete'
        }
        success {
            echo 'Success'
        }
        failure {
            echo 'Failure'
        }
    }

}
