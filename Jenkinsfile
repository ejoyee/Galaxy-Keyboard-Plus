pipeline {
  agent any

  environment {
    COMPOSE_FILE    = 'docker-compose-prod.yml'
    ENV_FILE        = '.env.prod'
    ANDROID_HOME    = '/opt/android-sdk'
    NODE_VERSION    = '18'
    FRONTEND_DIR    = 'front/frontend'
    APK_PATH        = 'android/app/build/outputs/apk/release/app-release.apk'
  }

  parameters {
    string(
      name: 'FORCE_SERVICES',
      defaultValue: '',
      description: '콤마(,)로 지정 시 해당 서비스만 빌드·배포 (예: gateway,auth,backend,rag,frontend)'
    )
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

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
          string(credentialsId: 'FIREBASE_CREDENTIALS_JSON_BASE64',           variable: 'FIREBASE_CREDENTIALS_JSON_BASE64'),
          string(credentialsId: 'FRONTEND_API_URL',         variable: 'API_URL')
        ]) {
          sh '''
            cp "$GCP_KEY_FILE" gcp-key.json
            chmod 644 gcp-key.json
            mkdir -p back/rag
            cp gcp-key.json back/rag/
          '''
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
FIREBASE_CREDENTIALS_JSON_BASE64=${FIREBASE_CREDENTIALS_JSON_BASE64}

ENV=prod
""".trim()
          sh "mkdir -p ${FRONTEND_DIR}"
          writeFile file: "${FRONTEND_DIR}/.env", text: """
API_URL=${API_URL}
ENV=prod
""".trim()
        }
      }
    }

    stage('Detect Changed Services') {
      steps {
        script {
          def diff = sh(
            script: "git diff --name-only ${env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: 'HEAD~1'} ${env.GIT_COMMIT}",
            returnStdout: true
          ).trim()
          def changed = diff.split('\n')
                            .findAll{ it }
                            .findAll{ it.startsWith('back/') || it.startsWith('front/frontend/') }
                            .collect{ p -> p.startsWith('front/frontend/') ? 'frontend' : p.tokenize('/')[1] }
                            .unique()
          def forced = params.FORCE_SERVICES?.trim() ? params.FORCE_SERVICES.split(',').collect{ it.trim() } : []
          env.CHANGED_SERVICES = (forced ?: changed).toSet().join(',')
          if (!env.CHANGED_SERVICES) {
            echo 'No service changes.'
            currentBuild.result = 'SUCCESS'
          } else {
            echo "Target services: ${env.CHANGED_SERVICES}"
          }
        }
      }
    }

    stage('Frontend CI/CD') {
      when {
        anyOf {
          expression { env.CHANGED_SERVICES?.split(',')?.contains('frontend') }
          expression { params.FORCE_SERVICES?.split(',')?.contains('frontend') }
        }
      }
      stages {
        stage('Prepare Android Directory') {
          steps {
            sh '''
              # Docker 이미지 캐시 정리
              docker image prune -f
              
              # 권한 문제 해결을 위해 root 사용자로 디렉토리 구조 설정
              sudo mkdir -p ${FRONTEND_DIR}/android/app/keystore
              sudo chmod -R 777 ${FRONTEND_DIR}/android
              
              echo "== Android 디렉토리 준비 완료 =="
            '''
          }
        }
        
        stage('Frontend Setup') {
          steps {
            dir(env.FRONTEND_DIR) {
              // 1) google-services.json 파일 직접 복사
              withCredentials([ file(credentialsId: 'google-services-json', variable: 'GOOGLE_SERVICES_JSON') ]) {
                sh '''
                  # root 권한으로 파일 복사
                  sudo cp "$GOOGLE_SERVICES_JSON" android/app/google-services.json
                  sudo chmod 644 android/app/google-services.json
                '''
              }
              
              // 2) npm install inside Docker (root 사용자로 실행)
              sh '''
                echo "== npm install =="
                docker run --rm \
                  -v "${WORKSPACE}/${FRONTEND_DIR}:/app" \
                  -w /app \
                  node:${NODE_VERSION} \
                  npm install --no-audit --no-fund
                echo "== npm install complete =="
              '''
            }
          }
        }

        stage('Android Build') {
          steps {
            dir(env.FRONTEND_DIR) {
              withCredentials([
                file(credentialsId: 'android-release-keystore', variable: 'KEYSTORE_FILE'),
                string(credentialsId: 'KEYSTORE_PASSWORD',     variable: 'KEYSTORE_PASSWORD'),
                string(credentialsId: 'KEY_ALIAS',             variable: 'KEY_ALIAS'),
                string(credentialsId: 'KEY_PASSWORD',          variable: 'KEY_PASSWORD')
              ]) {
                // 키스토어 파일을 root 권한으로 복사
                sh '''
                  sudo cp "$KEYSTORE_FILE" android/app/keystore/release.keystore
                  sudo chmod 644 android/app/keystore/release.keystore
                '''
              }
              sh '''
                echo "== Android build =="
                docker run --rm \
                  -v "${WORKSPACE}/${FRONTEND_DIR}:/app" \
                  -w /app \
                  cimg/android:2023.08.1 \
                  bash -c "cd android && echo MYAPP_RELEASE_STORE_FILE=keystore/release.keystore >> gradle.properties && echo MYAPP_RELEASE_KEY_ALIAS=${KEY_ALIAS} >> gradle.properties && echo MYAPP_RELEASE_STORE_PASSWORD=${KEYSTORE_PASSWORD} >> gradle.properties && echo MYAPP_RELEASE_KEY_PASSWORD=${KEY_PASSWORD} >> gradle.properties && chmod +x ./gradlew && ./gradlew --no-daemon clean assembleRelease"
                
                # 빌드 결과 확인
                if [ -f "android/app/build/outputs/apk/release/app-release.apk" ]; then
                  # 빌드 번호를 포함한 이름으로 APK 파일 복사
                  cp android/app/build/outputs/apk/release/app-release.apk android/app/build/outputs/apk/release/moca-app-${BUILD_NUMBER}.apk
                  echo "== APK 생성 성공: moca-app-${BUILD_NUMBER}.apk =="
                else
                  echo "ERROR: APK 파일이 생성되지 않았습니다."
                  exit 1
                fi
              '''
              // 생성된 APK 파일을 Jenkins 아티팩트로 보관
              archiveArtifacts artifacts: "android/app/build/outputs/apk/release/*.apk", fingerprint: true
            }
          }
        }

        stage('Deploy to Firebase') {
          steps {
            dir(env.FRONTEND_DIR) {
              withCredentials([
                file(  credentialsId: 'firebase-service-account', variable: 'FIREBASE_SA'),
                string(credentialsId: 'FIREBASE_TOKEN',            variable: 'FIREBASE_TOKEN'),
                string(credentialsId: 'FIREBASE_APP_ID',           variable: 'FIREBASE_APP_ID')
              ]) {
                sh '''
                  echo "== Firebase deploy =="
                  APK_FILE=$(find android/app/build/outputs/apk/release -name "moca-app-${BUILD_NUMBER}.apk" | head -1)
                  
                  # Firebase 서비스 계정 JSON 파일 복사
                  sudo cp "$FIREBASE_SA" firebase-key.json
                  sudo chmod 644 firebase-key.json
                  
                  # Firebase CLI를 Docker 컨테이너 내에서 실행하여 배포
                  docker run --rm \
                    -v "${WORKSPACE}/${FRONTEND_DIR}:/app" \
                    -w /app \
                    -e FIREBASE_TOKEN="$FIREBASE_TOKEN" \
                    -e FIREBASE_APP_ID="$FIREBASE_APP_ID" \
                    -e BUILD_NUMBER="$BUILD_NUMBER" \
                    node:${NODE_VERSION} \
                    bash -c "npm install -g firebase-tools && firebase appdistribution:distribute $APK_FILE --app \$FIREBASE_APP_ID --token \$FIREBASE_TOKEN --groups testers --release-notes \"Jenkins build #\${BUILD_NUMBER}\""
                  
                  echo "== Firebase deploy complete =="
                '''
              }
            }
          }
        }
      }
    }

    stage('Build & Deploy Backend') {
      when {
        expression { env.CHANGED_SERVICES.split(',').any { it != 'frontend' } }
      }
      steps {
        script {
          env.CHANGED_SERVICES.split(',').each { svc ->
            if (svc != 'frontend') {
              echo "▶ Building & deploying ${svc}"
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
      sh 'rm -f .env.prod gcp-key.json back/rag/gcp-key.json ${FRONTEND_DIR}/.env'
    }
    success { 
      echo '빌드 및 배포 성공 🎉' 
      echo 'APK 파일은 Jenkins 빌드 아티팩트에서 다운로드하실 수 있으며, Firebase App Distribution으로도 배포되었습니다.'
    }
    failure { echo '빌드 또는 배포 실패 ❗' }
  }
}