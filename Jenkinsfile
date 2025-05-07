pipeline {
  agent any

  environment {
    COMPOSE_FILE = 'docker-compose-prod.yml'
    ENV_FILE     = '.env.prod'
    ANDROID_HOME = '/opt/android-sdk'
    NODE_VERSION = '18'
    APK_PATH     = 'android/app/build/outputs/apk/release/app-release.apk'
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
          string(credentialsId: 'OPENAI_API_KEY',           variable: 'OPENAI'),
          // 프론트엔드 환경 변수 추가
          string(credentialsId: 'FRONTEND_API_URL',        variable: 'API_URL')
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

          // .env.prod 파일 생성
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

          // 프론트엔드 환경 변수 파일 생성
          writeFile file: 'front/frontend/.env', text: """
API_URL=${API_URL}
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

    /* 3) Frontend CI/CD */
    stage('Frontend CI/CD') {
      when {
        anyOf {
          expression { env.CHANGED_SERVICES.split(',').contains('frontend') }
          expression { params.FORCE_SERVICES?.split(',')?.contains('frontend') }
        }
      }
      stages {
        stage('Frontend Setup') {
          steps {
            dir('front/frontend') {
              // 로컬 node_modules 사용 대신 Docker 컨테이너 내에서 빌드
              sh '''
                docker run --rm -v $(pwd):/app -w /app node:18 npm install --no-audit --no-fund
              '''
              
              // google-services.json 파일 생성
              withCredentials([
                file(credentialsId: 'google-services-json', variable: 'GOOGLE_SERVICES_JSON')
              ]) {
                sh 'mkdir -p android/app'
                sh 'cp $GOOGLE_SERVICES_JSON android/app/google-services.json'
              }
            }
          }
        }
        
        stage('Android Build') {
          steps {
            // 안드로이드 빌드를 위한 Docker 이미지 사용
            sh '''
              docker run --rm \
                -v $(pwd)/front/frontend:/app \
                -w /app \
                -e ANDROID_HOME=/opt/android-sdk \
                cimg/android:2023.08.1 \
                sh -c "cd android && chmod +x ./gradlew && ./gradlew assembleRelease"
            '''
            
            // 빌드된 APK 저장
            archiveArtifacts artifacts: 'front/frontend/android/app/build/outputs/apk/release/*.apk', fingerprint: true
          }
        }
        
        stage('Deploy to Firebase') {
          steps {
            dir('front/frontend') {
              withCredentials([
                file(credentialsId: 'firebase-service-account', variable: 'FIREBASE_SA'),
                string(credentialsId: 'FIREBASE_TOKEN', variable: 'FIREBASE_TOKEN'),
                string(credentialsId: 'FIREBASE_APP_ID', variable: 'FIREBASE_APP_ID')
              ]) {
                // Docker 컨테이너를 사용하여 Firebase 배포
                sh '''
                  docker run --rm \
                    -v $(pwd):/app \
                    -v $FIREBASE_SA:/app/firebase-key.json \
                    -w /app \
                    -e GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-key.json \
                    -e FIREBASE_TOKEN=$FIREBASE_TOKEN \
                    node:18 \
                    sh -c "npm install -g firebase-tools && firebase appdistribution:distribute $APK_PATH --app $FIREBASE_APP_ID --token $FIREBASE_TOKEN --groups 'testers' --release-notes 'Jenkins 빌드 #${BUILD_NUMBER} - $(date)'"
                '''
                
                // 배포 링크 생성 및 출력
                script {
                  echo """
                  ======================================================
                  앱 배포가 완료되었습니다!
                  
                  1. Firebase App Distribution에서 테스터 초대를 확인하세요.
                  2. 직접 APK 다운로드: ${BUILD_URL}artifact/front/frontend/${APK_PATH}
                  ======================================================
                  """
                }
              }
            }
          }
        }
      }
    }

    /* 4) Build & Deploy Backend Services */
    stage('Build & Deploy') {
      when { 
        expression { 
          env.CHANGED_SERVICES?.trim() && 
          env.CHANGED_SERVICES.split(',').any { !it.equals('frontend') } 
        }
      }
      steps {
        script {
          env.CHANGED_SERVICES.split(',').each { svc ->
            if (svc != 'frontend') {
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
  }

  post {
    always {
      sh 'shred -u .env.prod || rm -f .env.prod'
      sh 'rm -f gcp-key.json'
      sh 'rm -f back/rag/gcp-key.json || true'
      sh 'rm -f front/frontend/.env || true'
    }
    success {
      echo '빌드 및 배포가 성공적으로 완료되었습니다!'
    }
    failure {
      echo 'Build failed. (메일 설정이 없으면 생략)'
    }
  }
}