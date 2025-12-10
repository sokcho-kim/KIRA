# KIRA 배포 가이드

> **2025-12-02 업데이트**: GitLab CI/CD 자동 배포 시스템 도입

이 문서는 KIRA 프로젝트의 **태그 기반 자동 배포** 프로세스를 설명합니다.

## 📋 목차

1. [배포 시스템 개요](#배포-시스템-개요)
2. [사전 준비](#사전-준비)
3. [GitLab Variables 설정](#gitlab-variables-설정)
4. [배포 프로세스](#배포-프로세스)
5. [자동 업데이트](#자동-업데이트)
6. [트러블슈팅](#트러블슈팅)

---

## 배포 시스템 개요

### 아키텍처

```
Git Tag Push (v0.9.16)
    ↓
GitLab CI/CD (kira-tags runner)
    ↓
┌─────────────────────────────────┐
│ 1. 버전 추출 및 업데이트          │
│    - package.json                │
│    - VitePress 문서 링크          │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 2. Electron 앱 빌드              │
│    - Apple 코드 사이닝            │
│    - Apple 공증 (notarization)   │
│    - Apple Silicon (arm64) 빌드    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 3. S3 배포                       │
│    - KIRA-{version}.dmg          │
│    - KIRA-{version}.zip          │
│    - latest-mac.yml (자동 업데이트)│
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 4. VitePress 문서 배포            │
│    - S3 루트에 HTML 배포          │
│    - 다운로드 링크 자동 업데이트   │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 5. CloudFront 캐시 무효화         │
└─────────────────────────────────┘
    ↓
✅ 배포 완료
```

### 핵심 파일

- **`.gitlab-ci.yml`**: CI/CD 파이프라인 정의
- **`deploy.sh`**: 배포 스크립트 (빌드 + S3 업로드)
- **`electron-app/package.json`**: 빌드 설정 및 버전 관리
- **`electron-app/main.js`**: 자동 업데이트 로직

---

## 사전 준비

### 1. Apple Developer 준비물

#### Developer ID Application 인증서
1. https://developer.apple.com/account/resources/certificates
2. "+" 버튼 → "Developer ID Application" 선택
3. CSR 생성 (Keychain Access):
   ```
   Keychain Access > Certificate Assistant >
   Request a Certificate from a Certificate Authority
   ```
4. CSR 업로드 → 인증서 다운로드
5. 다운로드한 `.cer` 파일 더블클릭하여 Keychain에 설치

#### App-Specific Password 생성
1. https://appleid.apple.com 로그인
2. "Sign-In and Security" → "App-Specific Passwords"
3. "+" 버튼으로 새 비밀번호 생성
4. 생성된 비밀번호 저장 (xxxx-xxxx-xxxx-xxxx 형식)

#### p12 인증서 내보내기
```bash
# Keychain Access에서
1. "Developer ID Application" 인증서 우클릭
2. "Export Developer ID Application..."
3. 파일명: kira-cert.p12
4. 비밀번호 설정 (CSC_KEY_PASSWORD에 사용)

# Base64 인코딩
base64 -i ~/Desktop/kira-cert.p12 | pbcopy
# 클립보드에 복사됨 → GitLab Variable CSC_LINK에 붙여넣기
```

### 2. AWS 준비물

- S3 버킷: `kira-releases` (ap-northeast-2)
- IAM User: S3 읽기/쓰기 권한
- CloudFront Distribution ID: `EU03W5ZNSG0E`

### 3. GitLab Runner 설정

**빌드 PC (macOS) 설정:**
```bash
# GitLab Runner 설치
brew install gitlab-runner

# Runner 등록
gitlab-runner register \
  --url https://git.projectbro.com \
  --token YOUR_REGISTRATION_TOKEN \
  --executor shell \
  --non-interactive

# Runner 시작
gitlab-runner start

# 상태 확인
gitlab-runner status
```

**필수 조건:**
- ✅ macOS (Apple 코드 사이닝 필요)
- ✅ Apple Silicon (M1/M2/M3) - arm64 빌드
- ✅ Node.js 22+
- ✅ AWS CLI 설치
- ✅ Xcode Command Line Tools

---

## GitLab Variables 설정

**GitLab 프로젝트 > Settings > CI/CD > Variables**

### AWS 관련 (3개)

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `AWS_ACCESS_KEY_ID` | IAM Access Key | ✅ | ✅ |
| `AWS_SECRET_ACCESS_KEY` | IAM Secret Key | ✅ | ✅ |
| `AWS_DEFAULT_REGION` | `ap-northeast-2` | ✅ | ❌ |

### Apple 코드 사이닝 (5개)

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `APPLE_ID` | your-apple-id@email.com | ✅ | ❌ |
| `APPLE_APP_SPECIFIC_PASSWORD` | xxxx-xxxx-xxxx-xxxx | ✅ | ✅ |
| `APPLE_TEAM_ID` | XXXXXXXXXX (10자리) | ✅ | ✅ |
| `CSC_LINK` | Base64 인코딩된 p12 파일 | ✅ | ❌ |
| `CSC_KEY_PASSWORD` | p12 파일 비밀번호 | ✅ | ✅ |

**참고:**
- `CSC_LINK`는 너무 길어서 Masked 불가
- `APPLE_TEAM_ID`는 https://developer.apple.com/account > Membership에서 확인

---

## 배포 프로세스

### 자동 배포 (Production)

```bash
# 1. 코드 변경사항 커밋
git add .
git commit -m "feat: Add new feature"
git push origin main

# 2. 태그 생성 및 Push
git tag v0.9.16
git push origin v0.9.16

# 3. GitLab CI가 자동 실행됨
# GitLab > CI/CD > Pipelines에서 진행 상황 확인
```

**자동 실행 단계:**
1. 태그에서 버전 추출 (`v0.9.16` → `0.9.16`)
2. `electron-app/package.json` 버전 업데이트
3. VitePress 문서 다운로드 링크 업데이트
4. Electron 앱 빌드 + 코드 사이닝 + 공증
5. S3 업로드:
   - `KIRA-X.X.X-arm64.dmg`
   - `KIRA-X.X.X-arm64-mac.zip`
   - `latest-mac.yml` (자동 업데이트용)
6. VitePress 문서 빌드 및 S3 업로드
7. CloudFront 캐시 무효화

**결과:**
- 📦 앱 다운로드: https://kira.krafton-ai.com/download/KIRA-X.X.X-arm64.dmg
- 📚 문서 사이트: https://kira.krafton-ai.com

### 테스트 빌드 (S3 업로드 없음)

```bash
# GitLab UI에서
# Pipelines > Run Pipeline > 브랜치 선택 > test_build 수동 실행
```

**차이점:**
- S3 업로드 안함
- 빌드 파일은 Artifacts로 다운로드 가능 (7일 보관)
- Apple 코드 사이닝은 건너뜀

### 로컬 테스트 (Legacy)

> ⚠️ **주의**: 로컬 배포는 권장하지 않습니다. GitLab CI/CD를 사용하세요.

```bash
# 전체 배포 프로세스 테스트 (로컬)
./deploy.sh

# 필수 환경변수 설정 (로컬 테스트 시)
export APPLE_ID="..."
export APPLE_APP_SPECIFIC_PASSWORD="..."
export APPLE_TEAM_ID="..."
export CSC_LINK="..."
export CSC_KEY_PASSWORD="..."
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="ap-northeast-2"
```

---

## 자동 업데이트

### 작동 원리

```
사용자 앱 실행
    ↓
5초 후 자동으로 S3 체크
    ↓
latest-mac.yml 다운로드
    ↓
현재 버전과 비교
    ↓
새 버전 발견
    ↓
┌─────────────────────────────┐
│ "업데이트 가능"              │
│ 새 버전 X.X.X이 있습니다.    │
│ [확인]                      │
└─────────────────────────────┘
    ↓
백그라운드 다운로드
    ↓
다운로드 완료
    ↓
┌─────────────────────────────┐
│ "업데이트 준비 완료"          │
│ 지금 재시작하시겠습니까?      │
│ [지금 재시작] [나중에]       │
└─────────────────────────────┘
    ↓
서버 중지 → 앱 재시작 → 업데이트 적용
```

### 다국어 지원

- **English**: "Update Available", "Version X.X.X is now available..."
- **한국어**: "업데이트 가능", "새 버전 X.X.X이 있습니다..."

사용자가 앱에서 선택한 언어로 자동 표시됩니다.

### S3 파일 구조

```
s3://kira-releases/
├── download/
│   ├── KIRA-X.X.X-arm64.dmg
│   ├── KIRA-X.X.X-arm64-mac.zip
│   └── latest-mac.yml              ← 최신 버전 정보
├── index.html                       ← VitePress 문서
├── getting-started.html
└── ...
```

**latest-mac.yml 내용:**
```yaml
version: X.X.X
files:
  - url: KIRA-X.X.X-arm64.dmg
    sha512: ...
    size: ...
path: KIRA-X.X.X-arm64.dmg
sha512: ...
releaseDate: '2025-12-02T...'
```

---

## 트러블슈팅

### 파이프라인 실패

#### "uv not found"
```bash
# 빌드 PC에서
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### "AWS credentials not found"
- GitLab Variables에 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` 확인
- Protected 체크 여부 확인

#### "Code signing failed"
- `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` 확인
- `CSC_LINK` base64 인코딩 확인
- Keychain에 인증서 존재 여부 확인

#### "Notarization failed"
- App-Specific Password 유효성 확인
- Apple Developer 계정 상태 확인
- 네트워크 연결 확인 (Apple 서버와 통신 필요)

### 자동 업데이트 작동 안 함

#### 사용자 앱에서 업데이트 감지 안 됨
1. S3에 `latest-mac.yml` 존재 확인:
   ```bash
   aws s3 ls s3://kira-releases/download/latest-mac.yml
   ```

2. `latest-mac.yml` 내용 확인:
   ```bash
   aws s3 cp s3://kira-releases/download/latest-mac.yml - | cat
   ```

3. CloudFront 캐시 확인:
   ```bash
   # 수동 캐시 무효화
   aws cloudfront create-invalidation --distribution-id EU03W5ZNSG0E --paths "/download/*"
   ```

#### 사용자 앱에서 다운로드 실패
- S3 파일 권한 확인 (public-read)
- CloudFront 정상 작동 확인
- 사용자 네트워크 상태 확인

### 버전 불일치

#### 태그와 실제 배포 버전이 다름
- `.gitlab-ci.yml`의 버전 추출 로직 확인
- `deploy.sh`의 버전 확인 로직 확인

#### VitePress 문서의 다운로드 링크가 잘못됨
```bash
# vitepress-app/scripts/sync-version.js 실행
cd vitepress-app
node scripts/sync-version.js
```

---

## 버전 관리 규칙

### Semantic Versioning

```
v{MAJOR}.{MINOR}.{PATCH}

예: v0.9.16
    └─ MAJOR: 0 (베타)
    └─ MINOR: 9 (기능 추가)
    └─ PATCH: 16 (버그 수정)
```

### 배포 주기

- **Patch**: 버그 수정, 문서 업데이트
- **Minor**: 새 기능 추가
- **Major**: 호환성 깨지는 변경

---

## 체크리스트

### 최초 설정 (1회만)

- [ ] GitLab Runner 설치 및 등록 (`kira-tags`)
- [ ] Apple Developer 인증서 발급
- [ ] GitLab Variables 설정 (8개)
- [ ] 빌드 PC에 Node.js, AWS CLI 설치
- [ ] S3 버킷 및 CloudFront 설정 확인

### 매 배포 시

- [ ] 변경사항 커밋 및 main 브랜치 push
- [ ] 태그 생성 (`git tag v0.9.X`)
- [ ] 태그 push (`git push origin v0.9.X`)
- [ ] GitLab 파이프라인 성공 확인
- [ ] S3 파일 업로드 확인
- [ ] 문서 사이트 업데이트 확인
- [ ] 자동 업데이트 테스트 (이전 버전 앱 실행)

---

## 기술 상세

### GitLab CI/CD 파이프라인 구조

**`.gitlab-ci.yml`:**
```yaml
stages:
  - build
  - deploy

deploy:
  stage: deploy
  tags:
    - kira-tags
  only:
    - tags
  before_script:
    # 환경변수 설정 및 dependencies 설치
  script:
    # 버전 추출 및 배포
  artifacts:
    paths:
      - electron-app/dist/*.dmg
      - electron-app/dist/*.zip
    expire_in: 30 days
```

### deploy.sh 스크립트 구조

```bash
#!/bin/bash
set -e

# Step 1: 현재 버전 확인
# Step 2: Electron 앱 빌드 및 S3 배포 (npm run deploy)
# Step 3: VitePress 문서 배포
# Step 4: CloudFront 캐시 무효화
```

### Electron Builder 설정 (package.json)

```json
{
  "build": {
    "mac": {
      "hardenedRuntime": true,
      "notarize": true
    },
    "publish": {
      "provider": "s3",
      "bucket": "kira-releases",
      "region": "ap-northeast-2",
      "path": "/download",
      "acl": "public-read"
    }
  }
}
```

### 자동 업데이트 설정 (main.js)

```javascript
// S3 Feed URL 설정
autoUpdater.setFeedURL({
  provider: 's3',
  bucket: 'kira-releases',
  region: 'ap-northeast-2',
  path: '/download'
});

// 앱 시작 5초 후 업데이트 체크
setTimeout(() => {
  autoUpdater.checkForUpdatesAndNotify();
}, 5000);
```

---

## 참고 자료

- **GitLab CI/CD 문서**: https://docs.gitlab.com/ee/ci/
- **electron-builder**: https://www.electron.build/
- **electron-updater**: https://www.electron.build/auto-update
- **Apple 공증 가이드**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- **AWS S3 문서**: https://docs.aws.amazon.com/s3/
- **CloudFront 문서**: https://docs.aws.amazon.com/cloudfront/

---

## 담당자

- **배포 시스템**: DevOps Team
- **문의**: GitLab Issues 또는 Slack #kira-dev

---

## Changelog

- **2025-12-02**: arm64 (Apple Silicon) 전용 빌드로 전환
  - Universal binary → arm64 only
  - 빌드 시간 50% 단축
  - Intel Mac 지원 종료

- **2025-12-02**: GitLab CI/CD 자동 배포 시스템 도입
  - 태그 기반 배포
  - Apple 코드 사이닝 자동화
  - 자동 업데이트 시스템 구축
  - 다국어 알림 지원 (EN/KO)
