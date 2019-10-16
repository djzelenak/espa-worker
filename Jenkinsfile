pipeline {
    //-- Run on any available worker (agent) --\\
    agent any
    environment {
    //-- Read the worker version number
    WORKER_VERSION = readFile "${env.WORKSPACE}/version.txt"

    //-- Remove '/' character from the git branch name if it is present
    WORKER_BRANCH = sh 'git rev-parse --abbrev-ref HEAD | tr / -'

    //-- Reference the docker hub repo for the worker
    WORKER_REPO = "usgseros/espa-worker"
    }
    
    echo 'Worker version ${env.WORKER_VERSION}'
    echo 'Current worker branch ${env.WORKER_BRANCH}'
    echo 'Worker repo is referenced as ${env.WORKER_REPO}'

    //-- Job Stages (Actions) --\\
    stages {

        stage('Build') {
            steps {
                echo 'Build steps here.'

                // Update workspace timestamp to prevent nightly cleanup script from removing workspace during a job run
                sh script: """
                    touch "${env.WORKSPACE}"
                """, label: "Update workspace timestamp - prevents workspace cleanup during job run"

                echo 'Building Docker Image from Dockerfile in project.'

                script {
                    //-- Build the image no matter which branch we are on
                    def customImage = docker.build("${WORKER_REPO}:${WORKER_BRANCH}-${WORKER_VERSION}", ".")
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
                    }
                    CUSTOM_IMAGE.withRun {
                        // Run unit tests from within the working directory
                        '--workdir /home/espa/espa-processing'
                        'nose2 --with-coverage'
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
                    echo 'Not publishing image'
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
