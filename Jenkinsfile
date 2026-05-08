pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/israrkazmi/shopsmart-app.git'
            }
        }
post {
    always {
        // 1. Process the test results
        junit 'results.xml'
        
        // 2. Send the dynamic email with escaped tokens
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
