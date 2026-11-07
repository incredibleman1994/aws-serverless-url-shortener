#!/usr/bin/env bash
# Build + deploy the stack, then upload the frontend and refresh the CDN cache.
# Usage: ./deploy.sh [stack-name] [alert-email]
set -euo pipefail

STACK="${1:-url-shortener}"
ALERT_EMAIL="${2:-}"

sam build
sam deploy \
  --stack-name "$STACK" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "AlertEmail=${ALERT_EMAIL}"

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

BUCKET=$(output BucketName)
DIST_ID=$(output DistributionId)

aws s3 sync frontend/ "s3://${BUCKET}/" --delete
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" > /dev/null

echo
echo "Deployed! Open: $(output SiteUrl)"
