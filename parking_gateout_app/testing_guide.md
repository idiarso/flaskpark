# Testing Guide for Gate-Out Workflow

## Prerequisites
1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Update the `.env` file with your database credentials
3. Start the Flask application:
```bash
python app.py
```

## Testing Workflow

### 1. Operator Login
First, get an authentication token:

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "operator@example.com",
    "password": "your-password"
  }'
```

Expected response:
```json
{
  "status": "success",
  "data": {
    "token": "your-jwt-token"
  },
  "message": "Login successful"
}
```

### 2. Process Vehicle Exit
Use the token to process a vehicle exit:

```bash
curl -X PUT http://localhost:5000/api/parking-sessions/exit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "ticketNumber": "TKT202503290219527426"
  }'
```

Expected response:
```json
{
  "status": "success",
  "data": {
    "ticketNumber": "TKT202503290219527426",
    "duration": "2.5 hours",
    "fee": 12500
  },
  "message": "Exit processed successfully"
}
```

### 3. Process Payment
After calculating the fee, process the payment:

```bash
curl -X POST http://localhost:5000/api/payments/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "ticketNumber": "TKT202503290219527426",
    "paymentMethod": "Cash"
  }'
```

Expected response:
```json
{
  "status": "success",
  "data": {
    "transactionId": "123",
    "paymentStatus": "COMPLETED"
  },
  "message": "Payment processed successfully"
}
```

## Testing with Postman

1. Create a new collection called "Parking Gate-Out"
2. Add three requests:

### Login Request
- Method: POST
- URL: http://localhost:5000/api/auth/login
- Headers: Content-Type: application/json
- Body (raw JSON):
```json
{
  "email": "operator@example.com",
  "password": "your-password"
}
```

### Exit Request
- Method: PUT
- URL: http://localhost:5000/api/parking-sessions/exit
- Headers: 
  - Content-Type: application/json
  - Authorization: Bearer {{token}}
- Body (raw JSON):
```json
{
  "ticketNumber": "TKT202503290219527426"
}
```

### Payment Request
- Method: POST
- URL: http://localhost:5000/api/payments/process
- Headers:
  - Content-Type: application/json
  - Authorization: Bearer {{token}}
- Body (raw JSON):
```json
{
  "ticketNumber": "TKT202503290219527426",
  "paymentMethod": "Cash"
}
```

## Common Test Cases

1. **Valid Exit Flow**:
   - Login as operator
   - Process exit with valid ticket
   - Process payment
   - Verify vehicle status is updated

2. **Invalid Scenarios**:
   - Try processing exit with invalid ticket number
   - Try processing payment for already paid ticket
   - Try accessing endpoints without authentication

3. **Edge Cases**:
   - Process exit for vehicle parked less than 1 hour
   - Process exit for vehicle parked more than 24 hours
   - Handle different payment methods (Cash/Card)

## Browser Testing

1. Open http://localhost:5000 in your browser
2. Log in using operator credentials
3. Navigate to the Exit page
4. Enter test ticket number: TKT202503290219527426
5. Click "Calculate Fee" to see the parking duration and fee
6. Select payment method and click "Process Payment"

## Monitoring Tips

1. Watch the Flask application logs for any errors
2. Check the database after each operation to verify:
   - Vehicle status is updated (IsParked = false)
   - Payment record is created
   - Exit time is recorded correctly

## Sample Test Data

Use these test ticket numbers:
- TKT202503290219527426 (valid ticket, vehicle still parked)
- TKT202503290219527427 (already exited vehicle)
- TKT202503290219527428 (non-existent ticket)
