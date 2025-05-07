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
                            .findAll { it }
                            .findAll { it.startsWith('back/') || it.startsWith('front/frontend/') }
                            .collect { path ->
                              path.startsWith('back/')           ? path.tokenize('/')[1]
                            : path.startsWith('front/frontend/') ? 'frontend'
                            : null }
                            .unique()
          def forced = params.FORCE_SERVICES?.trim()
                        ? params.FORCE_SERVICES.split(',').collect{ it.trim() }
                        : []
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
        stage('Frontend Setup') {
          steps {
            dir(env.FRONTEND_DIR) {
              // 1) 프로젝트 디렉토리 확인
              sh 'echo "Current directory" && pwd && ls -la'

              // 2) google-services.json 호스트에서 복사 (컨테이너 전 권한 문제 회피)
              withCredentials([ file(credentialsId: 'google-services-json', variable: 'GOOGLE_SERVICES_JSON') ]) {
                sh '''
                  mkdir -p android/app
                  cp "$GOOGLE_SERVICES_JSON" android/app/google-services.json
                  ls -la android/app
                '''
              }

              // 3) npm 설치 (docker run)
              sh '''
                echo "== npm 설치 시작 =="
                docker run --rm \
                  --volumes-from $(hostname) \
                  -w "${WORKSPACE}/${FRONTEND_DIR}" \
                  node:${NODE_VERSION} \
                  npm install --no-audit --no-fund
                echo "== npm 설치 완료 =="
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
                sh '''
                  mkdir -p android/app/keystore
                  cp "$KEYSTORE_FILE" android/app/keystore/release.keystore
                  cat >> android/gradle.properties << EOF
MYAPP_RELEASE_STORE_FILE=keystore/release.keystore
MYAPP_RELEASE_KEY_ALIAS=$KEY_ALIAS
MYAPP_RELEASE_STORE_PASSWORD=$KEYSTORE_PASSWORD
MYAPP_RELEASE_KEY_PASSWORD=$KEY_PASSWORD
EOF
                '''
              }
              sh '''
                echo "== Android 빌드 시작 =="
                docker run --rm \
                  --volumes-from $(hostname) \
                  -w "${WORKSPACE}/${FRONTEND_DIR}" \
                  cimg/android:2023.08.1 \
                  ./gradlew -p android assembleRelease
                echo "== Android 빌드 완료 =="
              '''
              archiveArtifacts artifacts: "android/app/build/outputs/apk/release/*.apk", fingerprint: true
            }
          }
        }

        stage('Deploy to Firebase') {
          steps {
            dir(env.FRONTEND_DIR) {
              withCredentials([
                file(credentialsId: 'firebase-service-account', variable: 'FIREBASE_SA'),
                string(credentialsId: 'FIREBASE_TOKEN',           variable: 'FIREBASE_TOKEN'),
                string(credentialsId: 'FIREBASE_APP_ID',          variable: 'FIREBASE_APP_ID')
              ]) {
                sh '''
                  echo "== Firebase 배포 시작 =="
                  APK_FILE=$(find android/app/build/outputs/apk/release -name "*.apk" | head -1)
                  firebase-service-account 파일로 인증
                  firebase appdistribution:distribute $APK_FILE --app $FIREBASE_APP_ID --token $FIREBASE_TOKEN --groups testers --release-notes "Jenkins 빌드 #${BUILD_NUMBER}"
                  echo "== Firebase 배포 완료 =="
                '''
              }
            }
          }
        }
      }
    }

    stage('Build & Deploy Backend') {
      when {
        expression {
          env.CHANGED_SERVICES?.split(',').any { it != 'frontend' }
        }
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
    success { echo '빌드 및 배포 성공🎉' }
    failure { echo '빌드 또는 배포 실패❗' }
  }
}
