pipeline {
    //-- Run on any available worker (agent) --\\
    agent any

    //-- Job Build Parameters --\\
    parameters {
        string(name: 'DOCKERTAG', defaultValue: '2.35.0-el7-beta.3', description: 'Docker image tagname')
    }

    //-- Job Stages (Actions) --\\
    stages {
        stage('Build') {
            steps {
                // Update workspace timestamp to prevent nightly cleanup script from removing workspace during a job run
                sh script: """
                    touch "${env.WORKSPACE}"
                """, label: "Update workspace timestamp - prevents workspace cleanup during job run"

                echo 'Building Docker Image from Dockerfile.espa in project.'

                script {
                    def customImage = docker.build("usgseros/espa-worker:${env.DOCKERTAG}", "-f Dockerfile.espa .")
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
			sh: """nose2 --with-coverage""", label: "Running unit tests"
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploy steps here.'

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


