pipeline {
    //-- Run on any available worker (agent) --\\
    agent any

    //-- Job Build Parameters --\\
    parameters {
        string(name: 'DOCKERTAG', defaultValue: '0.0.1', description: 'Docker image tagname')
    }


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
                    def customImage = docker.build("usgseros/espa-worker:${env.DOCKERTAG}", "-f Dockerfile .")
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
                        sh 'export OCDATAROOT=/usr/local/auxiliary/ocdata'
                        sh 'landsat_l2gen'
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
        // Report status back to GitLab (requires user with Developer access to project)
        success {
            echo 'Success'
        }
        failure {
            echo 'Failure'
        }
    }

}


