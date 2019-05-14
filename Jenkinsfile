pipeline {
    //-- Run on any available worker (agent) --\\
    agent any
    //-- Job Stages (Actions) --\\
    stages {
        stage('Build') {
            steps {
                echo 'Build steps here.'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing steps here.'
                // Execute script from repo, on worker
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



