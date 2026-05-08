pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/israrkazmi/shopsmart-app.git'
            }
        }
stage('Test') {
    steps {
        sh '''
            . venv/bin/activate
            # Generate the XML report that Jenkins can read
            pytest --junitxml=results.xml tests/
        '''
    }
}

post {
    always {
        // 1. Process the test results so Jenkins knows the pass/fail count
        junit 'results.xml'
        
        // 2. Send the dynamic email
        emailext (
            subject: "ShopSmart Build: ${currentBuild.fullDisplayName} - ${currentBuild.currentResult}",
            body: """
                Build Status: ${currentBuild.currentResult}
                
                --- TEST SUMMARY ---
                ${testCounts}
                
                Detailed Results:
                - Passed: ${TEST_COUNTS, var="pass"}
                - Failed: ${TEST_COUNTS, var="fail"}
                - Skipped: ${TEST_COUNTS, var="skip"}
                
                Check the full report and logs here: ${env.BUILD_URL}
            """,
            // This makes the 'To' field dynamic
            recipientProviders: [
                [$class: 'RequesterRecipientProvider'], // Sends to the person who clicked "Build"
                [$class: 'CulpritsRecipientProvider']   // Sends to the person who committed the code
            ],
            // Optional: keep your main email as a fallback/cc
            to: 'syedisrarkazmi091@gmail.com'
        )
    }
}
    }
