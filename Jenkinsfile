pipeline {
  agent any
  environment {
    COMPOSE_FILE = "docker-compose-prod.yml"
    ENV_FILE     = ".env.prod"
  }

  stages {
    /* 0. Checkout ---------------------------------------------- */
    stage('Checkout') { steps { checkout scm } }

    /* 0-1. Branch Gate – release 만 진행 ------------------------ */
    stage('Verify release branch') {
      steps {
        script {
          if (env.BRANCH_NAME != 'release') {
            echo "Branch '${env.BRANCH_NAME}' ⇒ 배포 대상 아님. 파이프라인 종료."
            currentBuild.result = 'SUCCESS'
            return
          }
        }
      }
    }

    /* 1. .env.prod 생성 (Credentials) -------------------------- */
    stage('Create .env.prod') {
      steps {
        withCredentials([
          string(credentialsId: 'POSTGRES_AUTH_USER',     variable: 'AUTH_USER'),
          string(credentialsId: 'POSTGRES_AUTH_PASSWORD', variable: 'AUTH_PW'),
          string(credentialsId: 'POSTGRES_AUTH_DB_NAME',  variable: 'AUTH_DB'),
          string(credentialsId: 'POSTGRES_SCHED_USER',    variable: 'SCHED_USER'),
          string(credentialsId: 'POSTGRES_SCHED_PASSWORD',variable: 'SCHED_PW'),
          string(credentialsId: 'POSTGRES_SCHED_DB_NAME', variable: 'SCHED_DB'),
          string(credentialsId: 'POSTGRES_SCHED_DB_NAME', variable: 'SCHED_DB'),
          string(credentialsId: 'PINECONE_KEY',             variable: 'PINECONE_KEY'),
          string(credentialsId: 'CLAUDE_API_KEY',             variable: 'CLAUDE_API_KEY'),
          string(credentialsId: 'OPENAI_API_KEY',         variable: 'OPENAI')
        ]) {
          // 필수 환경 변수 검증
          if (!AUTH_USER || !AUTH_PW || !JWT || !OPENAI) {
            error "필수 환경 변수가 설정되지 않았습니다."
          }
          
          writeFile file: '.env.prod', text: """
POSTGRES_AUTH_USER=${AUTH_USER}
POSTGRES_AUTH_PASSWORD=${AUTH_PW}
POSTGRES_AUTH_DB_NAME=${AUTH_DB}

POSTGRES_SCHED_USER=${SCHED_USER}
POSTGRES_SCHED_PASSWORD=${SCHED_PW}
POSTGRES_SCHED_DB_NAME=${SCHED_DB}

JWT_SECRET=${JWT}
OPENAI_API_KEY=${OPENAI}
ENV=prod
""".trim()
        }
      }
    }

    /* 2. 변경 서비스 탐지 -------------------------------------- */
    stage('Detect Changed Services') {
      steps {
        script {
          def diff = sh(
            script: "git diff --name-only ${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'} ${env.GIT_COMMIT}",
            returnStdout: true).trim()

          def changed = diff.split('\n')
                            .collect { it.tokenize('/')[0..1].join('/') }
                            .unique()
                            .findAll { it.startsWith('back/') }

          env.CHANGED_SERVICES = changed.join(',')
          if (changed.isEmpty()) {
            echo "No service changes."; currentBuild.result='SUCCESS'; return
          }
        }
      }
    }

    /* 3. Build & Deploy --------------------------------------- */
    stage('Build & Deploy') {
      when { expression { env.CHANGED_SERVICES && !env.CHANGED_SERVICES.isEmpty() } }
      steps {
        script {
          // Docker Compose 파일 존재 확인
          if (!fileExists(COMPOSE_FILE)) {
            error "${COMPOSE_FILE} 파일이 존재하지 않습니다."
          }
          
          env.CHANGED_SERVICES.split(',').each { path ->
            def svc = path.tokenize('/')[1]
            echo "▶ Building & deploying: ${svc}"
            try {
              sh """
                docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build ${svc}
                docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --no-deps ${svc}
              """
            } catch (Exception e) {
              echo "서비스 ${svc} 빌드/배포 중 오류 발생: ${e.message}"
              error "서비스 ${svc} 빌드/배포 실패"
            }
          }
        }
      }
    }
  }
}