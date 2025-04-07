# Test script for gate-out error cases
param(
    [Parameter(Mandatory=$true)]
    [string]$email,
    
    [Parameter(Mandatory=$true)]
    [string]$password
)

function Test-ApiCall {
    param(
        [string]$testName,
        [scriptblock]$apiCall
    )
    
    Write-Host "`nTesting: $testName" -ForegroundColor Yellow
    Write-Host "Expected: Should return error" -ForegroundColor Gray
    
    try {
        $response = & $apiCall
        $responseObj = $response | ConvertFrom-Json
        Write-Host "Response: $($responseObj.message)" -ForegroundColor $(
            if ($responseObj.status -eq "error") { "Green" } else { "Red" }
        )
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
    Write-Host "----------------------------------------"
}

# 1. Login first to get token
Write-Host "Logging in to get valid token..." -ForegroundColor Green
$loginResponse = curl -X POST http://localhost:5000/api/auth/login `
    -H "Content-Type: application/json" `
    -d "{`"email`":`"$email`",`"password`":`"$password`"}"

$responseObj = $loginResponse | ConvertFrom-Json
if ($responseObj.status -ne "success") {
    Write-Host "Login failed: $($responseObj.message)" -ForegroundColor Red
    exit
}

$token = $responseObj.data.token
Write-Host "Login successful! Token received.`n" -ForegroundColor Green

# 2. Test Cases

# Authentication Errors
Test-ApiCall "Missing Token" {
    curl -X PUT http://localhost:5000/api/parking-sessions/exit `
        -H "Content-Type: application/json" `
        -d "{`"ticketNumber`":`"TKT123`"}"
}

Test-ApiCall "Invalid Token" {
    curl -X PUT http://localhost:5000/api/parking-sessions/exit `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer invalid_token" `
        -d "{`"ticketNumber`":`"TKT123`"}"
}

# Exit Processing Errors
Test-ApiCall "Invalid Ticket Number" {
    curl -X PUT http://localhost:5000/api/parking-sessions/exit `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer $token" `
        -d "{`"ticketNumber`":`"INVALID_TICKET`"}"
}

Test-ApiCall "Missing Ticket Number" {
    curl -X PUT http://localhost:5000/api/parking-sessions/exit `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer $token" `
        -d "{}"
}

# Payment Processing Errors
Test-ApiCall "Payment Without Exit" {
    curl -X POST http://localhost:5000/api/payments/process `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer $token" `
        -d "{`"ticketNumber`":`"TKT123`",`"paymentMethod`":`"Cash`"}"
}

Test-ApiCall "Invalid Payment Method" {
    curl -X POST http://localhost:5000/api/payments/process `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer $token" `
        -d "{`"ticketNumber`":`"TKT123`",`"paymentMethod`":`"Bitcoin`"}"
}

Test-ApiCall "Already Paid Ticket" {
    curl -X POST http://localhost:5000/api/payments/process `
        -H "Content-Type: application/json" `
        -H "Authorization: Bearer $token" `
        -d "{`"ticketNumber`":`"PAID_TICKET`",`"paymentMethod`":`"Cash`"}"
}

Write-Host "`nError case testing completed!" -ForegroundColor Green
