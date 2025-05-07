pipeline {
  agent any

  environment {
    COMPOSE_FILE = 'docker-compose-prod.yml'
    ENV_FILE     = '.env.prod'
  }

  parameters {
    string(name: 'FORCE_SERVICES', defaultValue: '',
      description: '콤마(,)로 지정 시 해당 서비스만 빌드·배포 (예: gateway,auth,backend,rag,frontend)')
  }

  stages {
    /* 0) Checkout */
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    /* 1) .env.prod 생성 */
    stage('Create .env.prod') {
      steps {
        withCredentials([
          string(credentialsId: 'POSTGRES_AUTH_USER',      variable: 'AUTH_USER'),
          string(credentialsId: 'POSTGRES_AUTH_PASSWORD',  variable: 'AUTH_PW'),
          string(credentialsId: 'POSTGRES_AUTH_DB_NAME',   variable: 'AUTH_DB'),
          string(credentialsId: 'POSTGRES_SCHED_USER',     variable: 'SCHED_USER'),
          string(credentialsId: 'POSTGRES_SCHED_PASSWORD', variable: 'SCHED_PW'),
          string(credentialsId: 'POSTGRES_SCHED_DB_NAME',  variable: 'SCHED_DB'),
          string(credentialsId: 'PINECONE_API_KEY',         variable: 'PINECONE_API_KEY'),
          string(credentialsId: 'PINECONE_INDEX_NAME',      variable: 'PINECONE_INDEX_NAME'),
          file(  credentialsId: 'moca-457801-bfa12690864b.json', variable: 'GCP_KEY_FILE'),
          string(credentialsId: 'CLAUDE_API_KEY',           variable: 'CLAUDE_API_KEY'),
          string(credentialsId: 'OPENAI_API_KEY',           variable: 'OPENAI')
        ]) {
          // GCP 키 파일을 workspace 로 복사
          sh '''
            cp "$GCP_KEY_FILE" gcp-key.json
            chmod 644 gcp-key.json
            
            # 파일이 디렉토리가 아님을 확인
            if [ -d gcp-key.json ]; then
              echo "오류: gcp-key.json이 디렉토리로 생성되었습니다. 파일이어야 합니다."
              exit 1
            fi
            
            # RAG 서비스 디렉토리로 키 파일 복사
            mkdir -p back/rag
            cp gcp-key.json back/rag/
          '''

          // .env.prod 파일 생성 - PINECONE_KEY를 PINECONE_API_KEY로 변경
          writeFile file: '.env.prod', text: """
POSTGRES_AUTH_USER=${AUTH_USER}
POSTGRES_AUTH_PASSWORD=${AUTH_PW}
POSTGRES_AUTH_DB_NAME=${AUTH_DB}

POSTGRES_SCHED_USER=${SCHED_USER}
POSTGRES_SCHED_PASSWORD=${SCHED_PW}
POSTGRES_SCHED_DB_NAME=${SCHED_DB}

OPENAI_API_KEY=${OPENAI}
PINECONE_API_KEY=${PINECONE_API_KEY}
PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME}
CLAUDE_API_KEY=${CLAUDE_API_KEY}

ENV=prod
""".trim()
        }
      }
    }

    /* 2) 변경 서비스 감지 */
    stage('Detect Changed Services') {
      steps {
        script {
          def diff = sh(
            script: "git diff --name-only ${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'} ${env.GIT_COMMIT}",
            returnStdout: true
          ).trim()

          def changed = diff.split('\n')
                            .findAll { it }
                            .collect { it.trim() }
                            .findAll { it.startsWith('back/') || it.startsWith('front/frontend/') }
                            .collect { path ->
                              path.startsWith('back/')           ? path.tokenize('/')[1]
                            : path.startsWith('front/frontend/') ? 'frontend'
                            : null
                            }
                            .unique()

          def forced = params.FORCE_SERVICES?.trim()
                        ? params.FORCE_SERVICES.split(',').collect{ it.trim() }
                        : []

          def targets = (forced ?: changed) as Set
          env.CHANGED_SERVICES = targets.join(',')

          if (!env.CHANGED_SERVICES) {
            echo 'No service changes.'
            currentBuild.result = 'SUCCESS'
          } else {
            echo "Target services: ${env.CHANGED_SERVICES}"
          }
        }
      }
    }

    /* 3) Frontend CI/CD (Placeholder) */
    stage('Frontend CI/CD') {
      when {
        anyOf {
          expression { env.CHANGED_SERVICES.split(',').contains('frontend') }
          expression { params.FORCE_SERVICES?.split(',')?.contains('frontend') }
        }
      }
      steps {
        echo '⏳ Frontend CI/CD 단계는 아직 구현되지 않았습니다. Placeholder 동작입니다.'
      }
    }

    /* 4) Build & Deploy Backend Services */
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

  post {
    always {
      sh 'shred -u .env.prod || rm -f .env.prod'
      sh 'rm -f gcp-key.json'
      sh 'rm -f back/rag/gcp-key.json || true'
    }
    failure {
      echo 'Build failed. (메일 설정이 없으면 생략)'
    }
  }
}