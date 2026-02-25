#!/usr/bin/env pwsh
# Deploy script - auto-imports existing resources

$ErrorActionPreference = "Continue"

Write-Host "`n=== DigitalOcean AI Platform Deploy ===" -ForegroundColor Cyan

# Initialize
Write-Host "`n[1/3] Initializing Terraform..." -ForegroundColor Yellow
terraform init -upgrade | Out-Null

# Check if bucket is in state
Write-Host "[2/3] Checking existing resources..." -ForegroundColor Yellow
$stateList = terraform state list 2>&1

# Try to apply, capture errors
Write-Host "[3/3] Applying configuration..." -ForegroundColor Yellow
$output = terraform apply -auto-approve 2>&1 | Tee-Object -Variable applyResult

# Check for bucket exists error
if ($applyResult -match "BucketAlreadyExists.*status code: 409") {
    Write-Host "`nSpaces bucket already exists - importing..." -ForegroundColor Yellow
    
    # Extract bucket name from error or plan
    $bucketName = "ai-platform-bucket-482a9388"  # Default from previous runs
    if ($applyResult -match '"(ai-platform-bucket-[a-f0-9]+)"') {
        $bucketName = $matches[1]
    }
    
    Write-Host "Importing bucket: nyc3,$bucketName" -ForegroundColor Cyan
    terraform import "digitalocean_spaces_bucket.bucket" "nyc3,$bucketName"
    
    Write-Host "`nRetrying apply..." -ForegroundColor Yellow
    terraform apply -auto-approve
}

# Show outputs
Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
terraform output -no-color
