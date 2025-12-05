# Swagger Petstore API Documentation

## Overview
This API provides endpoints for managing pets, orders, and users in a petstore system. It implements role-based access control with guest, customer, store owner, and admin roles.

**Base URL:** `http://localhost:3002/api/v3`

## Authentication
Most write operations require JWT authentication. Get a token by logging in:

```http
GET /api/v3/user/login?username=customer1&password=password
```

Include the token in subsequent requests:
```http
Authorization: Bearer <your-jwt-token>
```

## Roles & Permissions

- **Guest**: Browse pets, view inventory (no auth needed)
- **Customer**: Place/cancel own orders, manage own profile
- **Store Owner**: Manage pets, approve orders, view all orders
- **Admin**: Full access, user management, override permissions

## Pet Endpoints

### Update Pet
```http
PUT /api/v3/pet
Authorization: Bearer <token> (store_owner, admin)
Content-Type: application/json

{
  "id": 1,
  "name": "Fluffy",
  "category": {"name": "Cat"},
  "photoUrls": ["https://example.com/photo.jpg"],
  "tags": [{"name": "friendly"}],
  "status": "available"
}
```

**Validation:** Only admin can change status from "sold" to "available"

### Add Pet
```http
POST /api/v3/pet
Authorization: Bearer <token> (store_owner, admin)
Content-Type: application/json

{
  "name": "Buddy",
  "category": {"name": "Dog"},
  "photoUrls": ["https://example.com/buddy.jpg"],
  "tags": [{"name": "playful"}],
  "status": "available"
}
```

### Find Pets by Status
```http
GET /api/v3/pet/findByStatus?status=available
Authorization: Bearer <token>
```

**Parameters:**
- `status` (required): available, pending, or sold

### Find Pets by Tags
```http
GET /api/v3/pet/findByTags?tags=friendly&tags=playful
Authorization: Bearer <token>
```

**Parameters:**
- `tags` (required): Array of tag names

### Get Pet by ID
```http
GET /api/v3/pet/1
```
**No authentication required**

### Update Pet with Form Data
```http
POST /api/v3/pet/1
Authorization: Bearer <token> (store_owner, admin)
Content-Type: application/json

{
  "name": "Updated Name",
  "status": "pending"
}
```

### Delete Pet
```http
DELETE /api/v3/pet/1
Authorization: Bearer <token> (store_owner, admin)
```

**Pre-condition:** Cannot delete pets with active orders

### Upload Pet Image
```http
POST /api/v3/pet/1/uploadImage
Authorization: Bearer <token> (store_owner, admin)
Content-Type: multipart/form-data

file: <binary-data>
additionalMetadata: "Photo taken in store"
```

## Store Endpoints

### Get Inventory
```http
GET /api/v3/store/inventory
Authorization: Bearer <token>
```

**Response:**
```json
{
  "data": {
    "available": 5,
    "pending": 2, 
    "sold": 3
  }
}
```

### Place Order
```http
POST /api/v3/store/order
Authorization: Bearer <token> (customer, store_owner, admin)
Content-Type: application/json

{
  "petId": 1,
  "quantity": 1,
  "shipDate": "2024-01-15T10:00:00Z",
  "status": "placed"
}
```

**Validations:**
- Pet must be "available" status
- Quantity must be exactly 1
- Creates order and changes pet status to "pending"

### Get Order
```http
GET /api/v3/store/order/1
Authorization: Bearer <token>
```

**Access Control:** Customers can only view their own orders. Store owners/admins can view any order.

### Cancel Order
```http
DELETE /api/v3/store/order/1
Authorization: Bearer <token>
```

**Validations:**
- Can only cancel orders with "placed" status
- Canceling returns pet status to "available"
- Customers can only cancel their own orders

## User Endpoints

### Create User
```http
POST /api/v3/user
Content-Type: application/json

{
  "username": "newuser",
  "firstName": "John",
  "lastName": "Doe", 
  "email": "john@example.com",
  "password": "securepassword",
  "phone": "555-1234",
  "userStatus": 0
}
```

**No authentication required**. New users get "customer" role by default.

### Create Multiple Users
```http
POST /api/v3/user/createWithList
Content-Type: application/json

[
  {
    "username": "user1",
    "password": "password1",
    "email": "user1@example.com"
  },
  {
    "username": "user2", 
    "password": "password2",
    "email": "user2@example.com"
  }
]
```

### Login
```http
GET /api/v3/user/login?username=customer1&password=password
```

**Response:**
```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Logout
```http
GET /api/v3/user/logout
Authorization: Bearer <token>
```

### Get User
```http
GET /api/v3/user/customer1
Authorization: Bearer <token>
```

**Access Control:** Users can only view their own profile. Admins can view any profile.

### Update User
```http
PUT /api/v3/user/customer1
Authorization: Bearer <token>
Content-Type: application/json

{
  "firstName": "Updated",
  "lastName": "Name",
  "email": "updated@example.com",
  "phone": "555-9999"
}
```

**Validations:**
- Users can only update their own profile
- Only admin can change user roles
- Role changes require admin privileges

### Delete User
```http
DELETE /api/v3/user/customer1
Authorization: Bearer <token> (admin only)
```

**Pre-condition:** Cannot delete users with active orders

## State Transitions

The API enforces these automatic state changes:

1. **Place Order**: Pet status changes from "available" → "pending"
2. **Cancel Placed Order**: Pet status changes from "pending" → "available"  
3. **Deliver Order**: Pet status changes from "pending" → "sold"

## Error Responses

All errors return JSON with this format:
```json
{
  "error": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (validation failed)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

## Sample Data

The API includes sample data:

**Users:**
- `admin` / `password` (admin role)
- `storeowner` / `password` (store_owner role)
- `customer1` / `password` (customer role)
- `customer2` / `password` (customer role)

**Pets:**
- ID 1: Buddy (Dog, available)
- ID 2: Fluffy (Cat, available)  
- ID 3: Tweety (Bird, pending)
- ID 4: Nemo (Fish, sold)
- ID 5: Max (Dog, available)

## Health Check

```http
GET /health
```

Returns API health status - no authentication required.