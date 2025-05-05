pipeline {
  agent any

  /*──────────────────[ 전역 환경 ]──────────────────*/
  environment {
    COMPOSE_FILE = 'docker-compose-prod.yml'
    ENV_FILE     = '.env.prod'
  }

  /*─────────────[ 파이프라인 매개변수 ]─────────────*/
  parameters {
    string(
      name: 'FORCE_SERVICES',
      defaultValue: '',
      description: '콤마(,)로 구분해 빌드·배포할 서비스명을 지정 (예: gateway,auth,scheduler,rag). 비워두면 diff 기반으로 동작'
    )
  }

  /*──────────────────[ 단계 ]──────────────────*/
  stages {

    /* 0) 소스 체크아웃 ------------------------------------------------*/
    stage('Checkout') { steps { checkout scm } }

    /* 1) .env.prod 생성 ------------------------------------------------*/
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
          writeFile file: '.env.prod', text: """
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

    /* 2) 변경 서비스 탐지 + 파라미터 병합 ------------------------------*/
    stage('Detect Changed Services') {
      steps {
        script {
          // 2-1. Git diff 기반 리스트
          def diff = sh(
            script: "git diff --name-only ${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'} ${env.GIT_COMMIT}",
            returnStdout:true
          ).trim()

          def changed = diff.split('\n')
                            .collect { it.trim() }
                            .findAll { it.startsWith('back/') }
                            .collect { p -> p.tokenize('/')[1] }   // 폴더명만
                            .unique()

          // 2-2. 파라미터가 비어 있지 않으면 우선 사용
          def forced = params.FORCE_SERVICES?.trim()
          def targets = forced ? forced.split(',').collect{ it.trim() }.unique() : changed

          env.CHANGED_SERVICES = targets.join(',')

          if (targets.isEmpty()) {
            echo 'No service changes.'
            currentBuild.result = 'SUCCESS'
          } else {
            echo "Target services: ${env.CHANGED_SERVICES}"
          }
        }
      }
    }

    /* 3) Build & Deploy ---------------------------------------------*/
    stage('Build & Deploy') {
      when { expression { env.CHANGED_SERVICES?.trim() } }
      steps {
        script {
          env.CHANGED_SERVICES.split(',').each { svc ->
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

  /*──────────────────[ 후처리 ]──────────────────*/
  post {
    always  { sh 'shred -u .env.prod || rm -f .env.prod' }
    failure {
      mail to: 'devops@example.com',
           subject: "Deploy Failed – ${env.JOB_NAME} #${env.BUILD_NUMBER}",
           body: "Check Jenkins logs."
    }
  }
}
