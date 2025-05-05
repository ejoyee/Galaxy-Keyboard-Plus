pipeline {
  agent any
  environment {
    COMPOSE_FILE = 'docker-compose-prod.yml'
    ENV_FILE     = '.env.prod'
  }

  stages {
    /********** 0. Checkout ****************************************/
    stage('Checkout') { steps { checkout scm } }

    /********** 1. .env.prod 생성 (Credentials) ********************/
    stage('Create .env.prod') {
      steps {
        withCredentials([
          string(credentialsId:'POSTGRES_AUTH_USER',     variable:'AUTH_USER'),
          string(credentialsId:'POSTGRES_AUTH_PASSWORD', variable:'AUTH_PW'),
          string(credentialsId:'POSTGRES_AUTH_DB_NAME',  variable:'AUTH_DB'),
          string(credentialsId:'POSTGRES_SCHED_USER',    variable:'SCHED_USER'),
          string(credentialsId:'POSTGRES_SCHED_PASSWORD',variable:'SCHED_PW'),
          string(credentialsId:'POSTGRES_SCHED_DB_NAME', variable:'SCHED_DB'),
          string(credentialsId:'PINECONE_KEY',           variable:'PINECONE_KEY'),
          string(credentialsId:'CLAUDE_API_KEY',         variable:'CLAUDE_API_KEY'),
          string(credentialsId:'OPENAI_API_KEY',         variable:'OPENAI')
        ]) {
          writeFile file:'.env.prod', text: """
POSTGRES_AUTH_USER=${AUTH_USER}
POSTGRES_AUTH_PASSWORD=${AUTH_PW}
POSTGRES_AUTH_DB_NAME=${AUTH_DB}

POSTGRES_SCHED_USER=${SCHED_USER}
POSTGRES_SCHED_PASSWORD=${SCHED_PW}
POSTGRES_SCHED_DB_NAME=${SCHED_DB}

OPENAI_API_KEY=${OPENAI}
PINECONE_KEY=${PINECONE_KEY}
CLAUDE_API_KEY=${CLAUDE_API_KEY}
ENV=prod
""".trim()
        }
      }
    }

    /********** 2. 변경 서비스 탐지 *******************************/
    stage('Detect Changed Services') {
      steps {
        script {
          def diff = sh(
            script: "git diff --name-only ${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'} ${env.GIT_COMMIT}",
            returnStdout:true).trim()

          def changed = diff.split('\n')
                            .collect { it.trim() }
                            .findAll { it.startsWith('back/') }
                            .collect { p ->
                                def parts = p.tokenize('/')
                                parts.size() >= 2 ? parts[0..1].join('/') : null
                            }
                            .findAll { it != null }
                            .unique()

          env.CHANGED_SERVICES = changed.join(',')
          if (changed.isEmpty()) {
            echo 'No service changes.'
            currentBuild.result = 'SUCCESS'
          }
        }
      }
    }

    /********** 3. Build & Deploy *********************************/
    stage('Build & Deploy') {
      when { expression { env.CHANGED_SERVICES?.trim() } }
      steps {
        script {
          env.CHANGED_SERVICES.split(',').each { path ->
            def svc = path.tokenize('/')[1]
            echo "▶  Building & deploying: ${svc}"
            sh """
              docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build ${svc}
              docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --no-deps ${svc}
            """
          }
        }
      }
    }
  }

  post {
    always  { sh 'shred -u .env.prod || rm -f .env.prod' }
    failure {
      mail to:'devops@example.com',
           subject:"Deploy Failed – ${env.JOB_NAME} #${env.BUILD_NUMBER}",
           body:"Check Jenkins logs."
    }
  }
}
