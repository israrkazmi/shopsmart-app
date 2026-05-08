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
                echo 'Starting ShopSmart App and Running 15 Selenium Test Cases...'
                sh '''
                    # Setup virtual environment
                    python3 -m venv venv
                    . venv/bin/activate
                    
                    # Install dependencies
                    pip install -r requirements.txt selenium pytest
                    
                    # Start the application in the background
                    python app.py & 
                    sleep 15 
                    
                    # Run all tests found in the tests folder
                    # This fixes the "file or directory not found" error
                    pytest tests/
                    
                    # Clean up the background process
                    pkill -f "python app.py" || true
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
        emailext (
            subject: "Status: ${currentBuild.fullDisplayName}",
            body: "Build finished with status: ${currentBuild.currentResult}",
            recipientProviders: [[$class: 'CulpritsRecipientProvider'], [$class: 'RequesterRecipientProvider']]
        )
    }
}
}
