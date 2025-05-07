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
        stage('Frontend Setup') {
          steps {
            dir(env.FRONTEND_DIR) {
              // 1) google-services.json 호스트에 복사 (권한 보장)
              withCredentials([ file(credentialsId: 'google-services-json', variable: 'GOOGLE_SERVICES_JSON') ]) {
                sh '''
                  mkdir -p android/app
                  cp "$GOOGLE_SERVICES_JSON" android/app/google-services.json
                  chmod 644 android/app/google-services.json
                '''
              }
              // 2) npm install inside Docker as current user, bind only project dir
              sh '''
                echo "== npm install =="
                docker run --rm \
                  -u $(id -u):$(id -g) \
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
                sh '''
                  mkdir -p android/app/keystore
                  cp "$KEYSTORE_FILE" android/app/keystore/release.keystore
                '''
              }
              sh '''
                echo "== Android build =="
                docker run --rm \
                  -u $(id -u):$(id -g) \
                  -v "${WORKSPACE}/${FRONTEND_DIR}:/app" \
                  -w /app \
                  cimg/android:2023.08.1 \
                  bash -c "cd android && echo MYAPP_RELEASE_STORE_FILE=keystore/release.keystore >> gradle.properties && echo MYAPP_RELEASE_KEY_ALIAS=${KEY_ALIAS} >> gradle.properties && echo MYAPP_RELEASE_STORE_PASSWORD=${KEYSTORE_PASSWORD} >> gradle.properties && echo MYAPP_RELEASE_KEY_PASSWORD=${KEY_PASSWORD} >> gradle.properties && ./gradlew assembleRelease"
                echo "== Android build complete =="
              '''
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
                  APK_FILE=$(find android/app/build/outputs/apk/release -name "*.apk" | head -1)
                  cp "$FIREBASE_SA" firebase-key.json
                  npm install -g firebase-tools
                  firebase appdistribution:distribute $APK_FILE --app $FIREBASE_APP_ID --token $FIREBASE_TOKEN --groups testers --release-notes "Jenkins build #${BUILD_NUMBER}"
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
    success { echo '빌드 및 배포 성공 🎉' }
    failure { echo '빌드 또는 배포 실패 ❗' }
  }
}
