pipeline {
    agent any

    stages {
        // ... (Checkout and other stages here)

        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
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
            // 1. Parse results so Jenkins variables are populated
            junit 'results.xml'
            
            // 2. Send the dynamic email
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
        } // Closes always
    } // Closes post
} // Closes pipeline
