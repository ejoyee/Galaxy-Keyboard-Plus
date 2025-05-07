pipeline {
  agent any

  environment {
    COMPOSE_FILE = 'docker-compose-prod.yml'
    ENV_FILE     = '.env.prod'
    ANDROID_HOME = '/opt/android-sdk'
    NODE_VERSION = '18'
    FRONTEND_DIR = 'front/frontend'
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
          writeFile file: "${FRONTEND_DIR}/.env", text: """
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
            // 프론트엔드 디렉토리로 이동
            dir(env.FRONTEND_DIR) {
              // 프로젝트 정보 출력
              sh 'echo "Current directory" && pwd && ls -la'
              
              // 볼륨 마운트 대신 Docker 이미지에 파일 복사 방식 사용
              sh '''
                echo "Docker 내부에 파일 복사 방식으로 Node.js 패키지 설치 시작"
                
                # 임시 디렉토리 생성
                TEMP_DIR=$(mktemp -d)
                
                # 현재 디렉토리 내용을 임시 디렉토리로 복사
                cp -r * $TEMP_DIR/
                cp .env $TEMP_DIR/ || true
                cp .eslintrc.js $TEMP_DIR/ || true
                cp .prettierrc.js $TEMP_DIR/ || true
                cp .watchmanconfig $TEMP_DIR/ || true
                
                # Docker 컨테이너에서 패키지 설치
                docker run --rm \
                  -v $TEMP_DIR:/app \
                  -w /app \
                  node:18 \
                  bash -c "ls -la && npm install --no-audit --no-fund"
                
                # 설치된 node_modules를 다시 프로젝트 디렉토리로 복사
                cp -r $TEMP_DIR/node_modules .
                
                # 임시 디렉토리 삭제
                rm -rf $TEMP_DIR
                
                echo "Node.js 패키지 설치 완료"
              '''
              
              // google-services.json 파일 생성
              withCredentials([
                file(credentialsId: 'google-services-json', variable: 'GOOGLE_SERVICES_JSON')
              ]) {
                sh 'mkdir -p android/app'
                sh 'cp "$GOOGLE_SERVICES_JSON" android/app/google-services.json'
                sh 'ls -la android/app'
              }
            }
          }
        }
        
        stage('Android Build') {
          steps {
            dir(env.FRONTEND_DIR) {
              // 안드로이드 빌드 준비
              withCredentials([
                file(credentialsId: 'android-release-keystore', variable: 'KEYSTORE_FILE'),
                string(credentialsId: 'KEYSTORE_PASSWORD', variable: 'KEYSTORE_PASSWORD'),
                string(credentialsId: 'KEY_ALIAS', variable: 'KEY_ALIAS'),
                string(credentialsId: 'KEY_PASSWORD', variable: 'KEY_PASSWORD')
              ]) {
                sh 'mkdir -p android/app/keystore'
                sh 'cp "$KEYSTORE_FILE" android/app/keystore/release.keystore'
                sh 'ls -la android/app/keystore'
                
                // gradle.properties 파일에 서명 설정 추가
                sh """
                cat >> android/gradle.properties << EOF
                MYAPP_RELEASE_STORE_FILE=keystore/release.keystore
                MYAPP_RELEASE_KEY_ALIAS=$KEY_ALIAS
                MYAPP_RELEASE_STORE_PASSWORD=$KEYSTORE_PASSWORD
                MYAPP_RELEASE_KEY_PASSWORD=$KEY_PASSWORD
                EOF
                cat android/gradle.properties
                """
              }
              
              // 안드로이드 빌드 수행 - 마운트 대신 복사 방식 사용
              sh '''
                echo "Android 빌드 시작 - 파일 복사 방식 사용"
                
                # 임시 디렉토리 생성
                TEMP_DIR=$(mktemp -d)
                
                # 현재 디렉토리 내용을 임시 디렉토리로 복사
                cp -r * $TEMP_DIR/
                cp .env $TEMP_DIR/ || true
                cp .eslintrc.js $TEMP_DIR/ || true
                cp .prettierrc.js $TEMP_DIR/ || true
                cp .watchmanconfig $TEMP_DIR/ || true
                
                # Android 빌드
                docker run --rm \
                  -v $TEMP_DIR:/app \
                  -w /app \
                  cimg/android:2023.08.1 \
                  bash -c "cd android && chmod +x ./gradlew && ./gradlew assembleRelease"
                
                # 빌드된 APK를 프로젝트 디렉토리로 복사
                mkdir -p android/app/build/outputs/apk/release
                cp -r $TEMP_DIR/android/app/build/outputs/apk/release/* android/app/build/outputs/apk/release/
                
                # 임시 디렉토리 삭제
                rm -rf $TEMP_DIR
                
                echo "Android 빌드 완료"
                echo "Build output directory:"
                find android -name "*.apk" || echo "APK 파일을 찾을 수 없습니다"
              '''
              
              // 빌드된 APK 저장
              archiveArtifacts artifacts: 'android/app/build/outputs/apk/release/*.apk', fingerprint: true, allowEmptyArchive: true
            }
          }
        }
        
        stage('Deploy to Firebase') {
          steps {
            dir(env.FRONTEND_DIR) {
              withCredentials([
                file(credentialsId: 'firebase-service-account', variable: 'FIREBASE_SA'),
                string(credentialsId: 'FIREBASE_TOKEN', variable: 'FIREBASE_TOKEN'),
                string(credentialsId: 'FIREBASE_APP_ID', variable: 'FIREBASE_APP_ID')
              ]) {
                // Firebase 배포 - 파일 복사 방식 사용
                sh '''
                  # APK 파일 찾기
                  APK_FILE=$(find android/app/build/outputs/apk/release -name "*.apk" 2>/dev/null | head -1)
                  
                  if [ -z "$APK_FILE" ]; then
                    echo "ERROR: APK 파일을 찾을 수 없습니다!"
                    find android -name "*.apk" || echo "APK 파일 없음"
                    exit 1
                  fi
                  
                  echo "배포할 APK 파일: $APK_FILE"
                  
                  # 임시 디렉토리 생성
                  TEMP_DIR=$(mktemp -d)
                  
                  # APK 파일 복사
                  cp "$APK_FILE" $TEMP_DIR/app-release.apk
                  
                  # Firebase 서비스 계정 키 복사
                  cp "$FIREBASE_SA" $TEMP_DIR/firebase-key.json
                  
                  # Firebase 배포
                  docker run --rm \
                    -v $TEMP_DIR:/app \
                    -w /app \
                    -e GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-key.json \
                    -e FIREBASE_TOKEN="$FIREBASE_TOKEN" \
                    -e FIREBASE_APP_ID="$FIREBASE_APP_ID" \
                    -e BUILD_NUMBER="$BUILD_NUMBER" \
                    node:18 \
                    bash -c "npm install -g firebase-tools && firebase appdistribution:distribute /app/app-release.apk --app $FIREBASE_APP_ID --token $FIREBASE_TOKEN --groups 'testers' --release-notes 'Jenkins 빌드 #${BUILD_NUMBER} - $(date)'"
                  
                  # 임시 디렉토리 삭제
                  rm -rf $TEMP_DIR
                '''
                
                // 배포 링크 생성 및 출력
                script {
                  def apkPath = sh(script: "find ${env.FRONTEND_DIR}/android/app/build/outputs/apk/release -name '*.apk' 2>/dev/null | head -1", returnStdout: true).trim()
                  
                  if (apkPath) {
                    echo """
                    ======================================================
                    앱 배포가 완료되었습니다!
                    
                    1. Firebase App Distribution에서 테스터 초대를 확인하세요.
                    2. 직접 APK 다운로드: ${BUILD_URL}artifact/${apkPath}
                    ======================================================
                    """
                  } else {
                    echo "WARNING: 배포가 완료되었지만 APK 파일 경로를 찾을 수 없습니다."
                  }
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
      sh "rm -f ${FRONTEND_DIR}/.env || true"
    }
    success {
      echo '빌드 및 배포가 성공적으로 완료되었습니다!'
    }
    failure {
      echo 'Build failed. (메일 설정이 없으면 생략)'
    }
  }
}