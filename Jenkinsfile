pipeline {
    agent any

    environment {
        // Ensuring the virtual env is used for all commands
        PATH = "${WORKSPACE}/venv/bin:${env.PATH}"
    }

    stages {
        stage('Cleanup & Setup') {
            steps {
                sh '''
                    # Kill any old instances to prevent port conflicts
                    pkill -f "python3 app.py" || true
                    pkill -f "pytest" || true
                    
                    # Setup Environment
                    python3 -m venv venv
                    pip install -r requirements.txt selenium pytest
                '''
            }
        }

        stage('Test') {
            steps {
                // We start the app in the background and then run tests
                sh '''
                    . venv/bin/activate
                    
                    # 1. Start Flask app in background
                    python3 app.py & 
                    
                    # 2. Wait for the app to actually be ready (important!)
                    sleep 10
                    
                    # 3. Run Selenium tests and generate XML report
                    pytest --junitxml=results.xml tests/
                    
                    # 4. Cleanup background app after tests
                    pkill -f "python3 app.py" || true
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
            // Parse the XML results so Jenkins "sees" the 15 tests
            junit 'results.xml'
            
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
