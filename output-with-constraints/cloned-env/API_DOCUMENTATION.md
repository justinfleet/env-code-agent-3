# Swagger Petstore API Documentation

## API Overview

This is a comprehensive Petstore API with role-based authentication and complex business logic for managing pets, orders, and users.

**Base URL:** `http://localhost:3002/api/v3`

## Authentication

The API uses JWT-based authentication. Most endpoints require authentication.

**Login:** `GET /api/v3/user/login?username={username}&password={password}`

Returns a JWT token that should be included in the `Authorization` header as `Bearer {token}`.

### User Roles

- **guest**: Unauthenticated user (can browse pets, view inventory, register, login)
- **customer**: Registered customer (can place/view/cancel own orders, manage own profile)
- **store_owner**: Store employee (can manage pets, view/approve/deliver all orders)
- **admin**: System administrator (full access, can manage users and relist sold pets)

## Endpoints

### Pet Management

#### GET /api/v3/pet/{petId}
**Description:** Find pet by ID  
**Authentication:** Not required  
**Parameters:**
- `petId` (path): Pet ID to retrieve

**Response:**
```json
{
  "id": 1,
  "name": "Buddy",
  "category": {
    "id": 1,
    "name": "Dogs"
  },
  "photoUrls": ["https://example.com/buddy.jpg"],
  "tags": [
    {"id": 1, "name": "friendly"},
    {"id": 2, "name": "energetic"}
  ],
  "status": "available"
}
```

#### GET /api/v3/pet/findByStatus
**Description:** Finds pets by status  
**Authentication:** Required  
**Allowed Roles:** All authenticated users  
**Parameters:**
- `status` (query): Pet status (available, pending, sold)

**Response:** Array of pet objects

#### GET /api/v3/pet/findByTags
**Description:** Finds pets by tags  
**Authentication:** Required  
**Allowed Roles:** All authenticated users  
**Parameters:**
- `tags` (query): Comma-separated list of tags

**Response:** Array of pet objects

#### POST /api/v3/pet
**Description:** Add a new pet to the store  
**Authentication:** Required  
**Allowed Roles:** store_owner, admin  
**Request Body:**
```json
{
  "name": "New Pet",
  "category": {
    "id": 1,
    "name": "Dogs"
  },
  "photoUrls": ["https://example.com/photo.jpg"],
  "tags": [
    {"id": 1, "name": "friendly"}
  ],
  "status": "available"
}
```

#### PUT /api/v3/pet
**Description:** Update an existing pet  
**Authentication:** Required  
**Allowed Roles:** store_owner, admin  
**Special Rules:** Only admin can change status from 'sold' to 'available'  
**Request Body:** Same as POST /api/v3/pet with `id` field

#### POST /api/v3/pet/{petId}
**Description:** Updates a pet with form data  
**Authentication:** Required  
**Allowed Roles:** store_owner, admin  
**Parameters:**
- `petId` (path): Pet ID to update

**Request Body:**
```json
{
  "name": "Updated Name",
  "status": "available"
}
```

#### DELETE /api/v3/pet/{petId}
**Description:** Deletes a pet  
**Authentication:** Required  
**Allowed Roles:** store_owner, admin  
**Pre-conditions:** Pet must not have active orders  
**Parameters:**
- `petId` (path): Pet ID to delete

#### POST /api/v3/pet/{petId}/uploadImage
**Description:** Uploads an image for a pet  
**Authentication:** Required  
**Allowed Roles:** store_owner, admin  
**Parameters:**
- `petId` (path): Pet ID

**Request Body:** multipart/form-data with `file` and optional `additionalMetadata`

### Store Operations

#### GET /api/v3/store/inventory
**Description:** Returns pet inventories by status  
**Authentication:** Required  
**Response:**
```json
{
  "available": 5,
  "pending": 2,
  "sold": 3
}
```

#### POST /api/v3/store/order
**Description:** Place an order for a pet  
**Authentication:** Required  
**Allowed Roles:** customer, store_owner, admin  
**Business Rules:**
- Pet must be available
- Quantity must be 1 (live animals)
- Pet cannot have existing active orders

**Request Body:**
```json
{
  "petId": 1,
  "quantity": 1,
  "shipDate": "2024-01-15",
  "status": "placed",
  "complete": false
}
```

**State Changes:** Pet status changes from 'available' to 'pending'

#### GET /api/v3/store/order/{orderId}
**Description:** Find purchase order by ID  
**Authentication:** Required  
**Authorization:** Customers can only view their own orders; store_owner/admin can view all  
**Parameters:**
- `orderId` (path): Order ID

#### PUT /api/v3/store/order/{orderId}
**Description:** Update an order  
**Authentication:** Required  
**Business Rules:**
- Cannot modify delivered orders
- Only store_owner/admin can approve or mark as delivered
- Customers can only modify their own orders

**State Changes:** When status becomes 'delivered', pet status changes to 'sold'

#### DELETE /api/v3/store/order/{orderId}
**Description:** Delete/cancel an order  
**Authentication:** Required  
**Authorization:** Customers can only cancel their own orders  
**Business Rules:**
- Only 'placed' orders can be cancelled
- Cannot cancel delivered orders

**State Changes:** Pet status returns to 'available' when placed order is cancelled

### User Management

#### GET /api/v3/user/login
**Description:** Logs user into the system  
**Parameters:**
- `username` (query): Username
- `password` (query): Password

**Response:**
```json
{
  "token": "jwt-token-here",
  "expires": "2024-01-15T12:00:00Z"
}
```

#### GET /api/v3/user/logout
**Description:** Logs out current user session  

#### POST /api/v3/user
**Description:** Create user (registration)  
**Request Body:**
```json
{
  "username": "johndoe",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john@example.com",
  "password": "password123",
  "phone": "+1234567890",
  "userStatus": 0
}
```

#### POST /api/v3/user/createWithList
**Description:** Creates list of users  
**Authentication:** Required  
**Allowed Roles:** admin only  
**Request Body:** Array of user objects

#### GET /api/v3/user/{username}
**Description:** Get user by username  
**Authentication:** Required  
**Authorization:** Users can only view their own profile; admin can view all

#### PUT /api/v3/user/{username}
**Description:** Update user  
**Authentication:** Required  
**Authorization:** Users can only edit their own profile; admin can edit all  
**Special Rules:** Only admin can change user roles

#### DELETE /api/v3/user/{username}
**Description:** Delete user  
**Authentication:** Required  
**Allowed Roles:** admin only  
**Pre-conditions:** User must not have active orders

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- **400**: Bad Request (validation errors, business rule violations)
- **401**: Unauthorized (missing or invalid authentication)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found (resource doesn't exist)
- **500**: Internal Server Error

## Business Logic

### State Transitions
- Creating an order changes pet status: available → pending
- Delivering an order changes pet status: pending → sold  
- Cancelling a placed order returns pet status: pending → available

### Validation Rules
- Pets must be 'available' to be ordered
- Order quantity must be exactly 1 for live animals
- Only one active order per pet at a time
- Cannot modify or cancel delivered orders
- Only placed orders can be cancelled

### Authorization Rules
- Customers can only access their own orders and profile
- Store owners can manage pets and view/process all orders
- Only admins can relist sold pets, manage users, and change roles
- Resource ownership is enforced with bypass for privileged roles