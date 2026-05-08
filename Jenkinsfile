pipeline {
    agent any

    environment {
        // Adding Python to PATH just in case
        PATH = "/var/lib/jenkins/workspace/shopsmart-pipeline/venv/bin:$PATH"
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulling your ShopSmart code
                git branch: 'main', url: 'https://github.com/israrkazmi/shopsmart-app.git'
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt selenium pytest
                    # Run tests and generate the XML results file
                    pytest --junitxml=results.xml tests/
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t shopsmart-app .'
            }
        }
    }

    post {
        always {
            // 1. Tell Jenkins to read the test results file
            junit 'results.xml'
            
            // 2. Send the dynamic email to the requester (you or Qasim)
            emailext (
                subject: "ShopSmart Build: ${currentBuild.fullDisplayName} - ${currentBuild.currentResult}",
                body: """
                    Build Status: ${currentBuild.currentResult}
                    
                    --- TEST SUMMARY ---
                    \${testCounts}
                    
                    Detailed Breakdown:
                    - Passed: \${TEST_COUNTS, var="pass"}
                    - Failed: \${TEST_COUNTS, var="fail"}
                    - Skipped: \${TEST_COUNTS, var="skip"}
                    
                    Check the full report and logs here: ${env.BUILD_URL}
                """,
                recipientProviders: [
                    [$class: 'RequesterRecipientProvider'], 
                    [$class: 'CulpritsRecipientProvider']
                ],
                to: 'syedisrarkazmi091@gmail.com'
            )
        }
    }
}
