#!/usr/bin/env bash
# Remove everything this project created (avoids leftover AWS costs).
# Usage: ./teardown.sh [stack-name]
set -euo pipefail

STACK="${1:-url-shortener}"

BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)

aws s3 rm "s3://${BUCKET}" --recursive
sam delete --stack-name "$STACK" --no-prompts
