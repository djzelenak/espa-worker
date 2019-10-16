pipeline {
    //-- Run on any available worker (agent) --\\
    agent any

    env.WORKER_VERSION = $(head -n1 version.txt)
    echo "Worker version ${env.WORKER_VERSION}"

    echo "Working on env.BRANCH_NAME"

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
                    def customImage = docker.build("usgseros/espa-worker:${env.BRANCH_NAME}-${env.WORKER_VERSION}", ".")
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
                        --workdir '/home/espa/espa-processing'
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
                    // Build for any branch, but only push for develop and master branches
                    if (env.BRANCH_NAME == 'master') {
                        // Specify the Dockerhub registry and Jenkins stored credentials
                        docker.withRegistry('https://index.docker.io/v1/', 'espa-docker-hub-credentials') {
                            // Push previously built image to registry
                            CUSTOM_IMAGE.push()
                        }
                    }
                    if (env.BRANCH_NAME == 'develop') {
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
