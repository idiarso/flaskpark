[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$username,
    
    [Parameter(Mandatory=$true)]
    [string]$password
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
                $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
                $errorMessage = $reader.ReadToEnd()
                $reader.Close()
            }
            catch {}
        }
        
        if ($statusCode -eq 429) {
            Write-Host "Rate limit exceeded" -ForegroundColor Yellow
            return @{
                status = "rate_limited"
                message = $errorMessage
            }
        }
        else {
            Write-Host "Request failed (Status: $statusCode)" -ForegroundColor Red
            Write-Host "Error: $errorMessage" -ForegroundColor Red
            return @{
                status = "error"
                message = $errorMessage
            }
        }
    }
}

# Function to get authentication token
function Get-AuthToken {
    param(
        [string]$username,
        [string]$password
    )
    
    $loginUrl = "$baseUrl/auth/login"
    $body = @{
        username = $username
        password = $password
    } | ConvertTo-Json
    
    Write-Host "Making Login..."
    try {
        $response = Invoke-WebRequest -Uri $loginUrl -Method Post -Body $body -ContentType "application/json"
        $result = $response.Content | ConvertFrom-Json
        
        if ($response.StatusCode -eq 200 -and $result.token) {
            return $result.token
        } else {
            Write-Error "Login response did not contain a token"
            exit 1
        }
    } catch {
        Write-Host "Request failed (Status: $($_.Exception.Response.StatusCode))"
        Write-Host "Error: $($_.Exception.Message)"
        exit 1
    }
}

# Function to test rate limiting
function Test-RateLimit {
    param(
        [string]$token
    )
    
    $testUrl = "$baseUrl/parking-sessions/active"
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    $requestCount = 110
    $requestDelay = 50 # milliseconds
    $rateLimit = 100 # requests per minute
    
    Write-Host "Testing rate limiting by making ${requestCount} requests..."
    Write-Host "Rate limit: ${rateLimit} requests per minute"
    Write-Host "Request delay: ${requestDelay} ms`n"
    
    $results = @()
    $startTime = Get-Date
    
    for ($i = 1; $i -le $requestCount; $i++) {
        Write-Host "Making Request ${i}..."
        $requestStart = Get-Date
        
        try {
            $response = Invoke-WebRequest -Uri $testUrl -Headers $headers -Method Get
            $duration = ((Get-Date) - $requestStart).TotalMilliseconds
            Write-Host "Request ${i}: Success (${duration} ms)"
            $results += [PSCustomObject]@{
                RequestNumber = $i
                Status = "Success"
                Duration = $duration
                Timestamp = Get-Date
            }
        } catch {
            $duration = ((Get-Date) - $requestStart).TotalMilliseconds
            if ($_.Exception.Response.StatusCode -eq 429) {
                Write-Host "Rate limit exceeded"
                Write-Host "Request ${i}: Rate limited (${duration} ms)"
                $results += [PSCustomObject]@{
                    RequestNumber = $i
                    Status = "RateLimited"
                    Duration = $duration
                    Timestamp = Get-Date
                }
            } else {
                Write-Host "Request failed (Status: $($_.Exception.Response.StatusCode))"
                Write-Host "Error: $($_.Exception.Message)"
                $results += [PSCustomObject]@{
                    RequestNumber = $i
                    Status = "Error"
                    Duration = $duration
                    Timestamp = Get-Date
                }
            }
        }
        
        Start-Sleep -Milliseconds $requestDelay
    }
    
    $endTime = Get-Date
    $totalDuration = ($endTime - $startTime).TotalSeconds
    $requestsPerMinute = $requestCount / ($totalDuration / 60)
    
    $successCount = ($results | Where-Object { $_.Status -eq "Success" }).Count
    $rateLimitCount = ($results | Where-Object { $_.Status -eq "RateLimited" }).Count
    $errorCount = ($results | Where-Object { $_.Status -eq "Error" }).Count
    
    Write-Host "`nTest Results:"
    Write-Host "Duration: $($totalDuration.ToString("0.00")) seconds"
    Write-Host "Requests per minute: $($requestsPerMinute.ToString("0.00"))"
    Write-Host "Successful requests: ${successCount}"
    Write-Host "Rate limited requests: ${rateLimitCount}"
    Write-Host "Error requests: ${errorCount}"
    
    # Save results to CSV
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $csvPath = "rate_limit_test_${timestamp}.csv"
    $results | Export-Csv -Path $csvPath -NoTypeInformation
    Write-Host "`nDetailed results saved to: ${csvPath}"
}

# Main execution
Write-Host "Starting rate limit test..."
$token = Get-AuthToken -username $username -password $password
Write-Host "Authentication successful, testing rate limiting..."
Test-RateLimit -token $token
