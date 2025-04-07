param(
    [Parameter(Mandatory=$true)]
    [string]$username,
    
    [Parameter(Mandatory=$true)]
    [string]$password,
    
    [Parameter(Mandatory=$true)]
    [string]$sessionId
)

# Base URL
$baseUrl = "http://localhost:3001/api"

# Function to make API request
function Invoke-ApiRequest {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [string]$Body,
        [hashtable]$Headers = @{},
        [string]$Description = "API request"
    )
    
    try {
        Write-Host "Making $Description..." -ForegroundColor Gray
        
        $params = @{
            Uri = $Uri
            Method = $Method
            Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body
            if (-not $Headers.ContainsKey("Content-Type")) {
                $params.Headers["Content-Type"] = "application/json"
            }
        }
        
        $response = Invoke-WebRequest @params
        return $response.Content | ConvertFrom-Json
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $errorMessage = $_.Exception.Message
        
        if ($_.Exception.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $errorMessage = $reader.ReadToEnd()
                $reader.Close()
            }
            catch {}
        }
        
        Write-Host "$Description failed (Status: $statusCode)" -ForegroundColor Red
        Write-Host "Error: $errorMessage" -ForegroundColor Red
        exit 1
    }
}

# Function to get authentication token
function Get-AuthToken {
    param(
        [string]$username,
        [string]$password
    )
    
    $body = @{
        username = $username
        password = $password
    } | ConvertTo-Json
    
    $response = Invoke-ApiRequest `
        -Uri "$baseUrl/auth/login" `
        -Method "POST" `
        -Body $body `
        -Description "Login"
    
    if ($response.token) {
        return $response.token
    }
    else {
        Write-Error "Login response did not contain a token"
        exit 1
    }
}

# Function to get active sessions
function Get-ActiveSessions {
    param([string]$token)
    
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    return Invoke-ApiRequest `
        -Uri "$baseUrl/parking-sessions/active" `
        -Headers $headers `
        -Description "Get active sessions"
}

# Function to test gate out
function Test-GateOut {
    param(
        [string]$token,
        [string]$sessionId
    )
    
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    $body = @{
        exitPoint = "GATE_OUT_1"
    } | ConvertTo-Json
    
    $response = Invoke-ApiRequest `
        -Uri "$baseUrl/parking-sessions/$sessionId/end" `
        -Method "POST" `
        -Headers $headers `
        -Body $body `
        -Description "Process gate out"
    
    Write-Host "`nGate out successful!" -ForegroundColor Green
    
    if ($response.session) {
        Write-Host "`nSession details:" -ForegroundColor Cyan
        $response.session | Format-List
    }
    
    if ($response.transaction) {
        Write-Host "`nTransaction details:" -ForegroundColor Cyan
        $response.transaction | Format-List
    }
}

# Main execution
Write-Host "Starting gate out test..." -ForegroundColor Cyan

# Step 1: Login
$token = Get-AuthToken -username $username -password $password
Write-Host "Login successful!" -ForegroundColor Green

# Step 2: Get active sessions (optional, for verification)
Write-Host "`nChecking active sessions..." -ForegroundColor Cyan
$activeSessions = Get-ActiveSessions -token $token
Write-Host "Found $($activeSessions.sessions.Count) active sessions" -ForegroundColor Gray

# Step 3: Process gate out
Write-Host "`nProcessing gate out..." -ForegroundColor Cyan
Test-GateOut -token $token -sessionId $sessionId

Write-Host "`nTest completed successfully!" -ForegroundColor Green
