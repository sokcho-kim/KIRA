#!/bin/bash

# KIRA 자동 배포 스크립트
# Electron 앱과 VitePress 문서를 함께 배포합니다.
#
# 사용법:
#   ./deploy.sh                    # package.json 버전 사용
#   ./deploy.sh 0.1.7              # 특정 버전 지정
#   ./deploy.sh 0.1.7 --skip-notarize  # notarization 스킵
#   ./deploy.sh --skip-notarize    # 현재 버전 + notarization 스킵

set -e  # 에러 발생 시 스크립트 중단

# AWS 리전 설정 (S3 버킷: kira-releases)
export AWS_DEFAULT_REGION=ap-northeast-2

# 인자 파싱
SKIP_NOTARIZE=false
VERSION_ARG=""

for arg in "$@"; do
  case $arg in
    --skip-notarize)
      SKIP_NOTARIZE=true
      ;;
    *)
      if [[ $arg =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        VERSION_ARG=$arg
      fi
      ;;
  esac
done

echo "🚀 KIRA 배포 시작..."
echo ""

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")"

# ===========================
# 1. 버전 설정
# ===========================
echo "📦 Step 1: 버전 설정"
cd electron-app

if [ -n "$VERSION_ARG" ]; then
  npm version $VERSION_ARG --no-git-tag-version
  CURRENT_VERSION=$VERSION_ARG
  echo "   지정 버전: $CURRENT_VERSION"
else
  CURRENT_VERSION=$(node -p "require('./package.json').version")
  echo "   현재 버전: $CURRENT_VERSION"
fi

if [ "$SKIP_NOTARIZE" = true ]; then
  echo "   ⚠️  Notarization 스킵"
  export CSC_IDENTITY_AUTO_DISCOVERY=false
fi

echo ""
cd ..

# ===========================
# 2. 문서 내 버전 업데이트
# ===========================
echo "📝 Step 2: 문서 내 버전 업데이트"
# 다운로드 링크의 버전만 교체 (KIRA-X.X.X-arm64.dmg)
find vitepress-app -name "*.md" -exec sed -i '' -E "s/KIRA-[0-9]+\.[0-9]+\.[0-9]+-(universal|arm64)\.dmg/KIRA-$CURRENT_VERSION-arm64.dmg/g" {} \;
echo "   ✅ 문서 버전 $CURRENT_VERSION 으로 업데이트"
echo ""

# ===========================
# 3. Electron 앱 빌드 및 배포
# ===========================
echo "🔨 Step 3: Electron 앱 빌드 및 S3 배포"
cd electron-app
npm run deploy
echo "   ✅ Electron 앱 배포 완료"
echo ""
cd ..

# ===========================
# 4. VitePress 문서 배포
# ===========================
echo "📚 Step 4: VitePress 문서 배포"
cd vitepress-app
npm run docs:build
aws s3 sync .vitepress/dist s3://kira-releases --delete --exclude 'download/*'
echo "   ✅ VitePress 문서 배포 완료"
echo ""
cd ..

# ===========================
# 5. CloudFront 캐시 무효화
# ===========================
echo "🔄 Step 5: CloudFront 캐시 무효화"
aws cloudfront create-invalidation --distribution-id EU03W5ZNSG0E --paths "/*"
echo "   ✅ CloudFront 캐시 무효화 완료"
echo ""

# ===========================
# 완료
# ===========================
echo "✨ 배포 완료!"
echo ""
echo "📦 Electron 앱: https://kira.krafton-ai.com/download/KIRA-$CURRENT_VERSION-arm64.dmg"
echo "📚 문서 사이트: https://kira.krafton-ai.com"
echo ""
echo "🎉 버전 $CURRENT_VERSION 배포가 성공적으로 완료되었습니다!"
