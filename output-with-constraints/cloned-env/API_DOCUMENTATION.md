# Petstore API Documentation

## Overview

The Petstore API is a RESTful web service for managing a pet store. It provides functionality for managing pets, orders, and users with role-based access control.

**Base URL:** `http://localhost:3002/api/v3`

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication via the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

### Getting an Access Token

Use the login endpoint to get an access token:

```
GET /api/v3/user/login?username=<username>&password=<password>
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires": "2024-01-16T10:00:00.000Z"
}
```

## Roles and Permissions

- **guest**: Unauthenticated users can browse pets and view inventory
- **customer**: Can place orders, view own orders, manage own profile
- **store_owner**: Can manage pets, view all orders, approve/deliver orders
- **admin**: Full system access, can manage users and override restrictions

## Endpoints

### Pets

#### POST /api/v3/pet
Add a new pet to the store.

**Auth Required:** Yes (store_owner, admin)

**Request Body:**
```json
{
  "name": "string",
  "category": {
    "id": "number",
    "name": "string"
  },
  "photoUrls": ["string"],
  "tags": [{"name": "string"}],
  "status": "available|pending|sold"
}
```

**Response:**
```json
{
  "id": "number",
  "name": "string",
  "category": {"id": "number", "name": "string"},
  "photoUrls": ["string"],
  "tags": [{"id": "number", "name": "string"}],
  "status": "string"
}
```

#### PUT /api/v3/pet
Update an existing pet.

**Auth Required:** Yes (store_owner, admin)

**Request Body:** Same as POST

**Response:** Updated pet object

**Business Rules:**
- Only admin can change sold pets back to available
- Status transitions are validated

#### GET /api/v3/pet/findByStatus
Find pets by status.

**Auth Required:** Yes

**Query Parameters:**
- `status`: available|pending|sold

**Response:** Array of pet objects

#### GET /api/v3/pet/findByTags
Find pets by tags.

**Auth Required:** Yes

**Query Parameters:**
- `tags`: Array of tag names

**Response:** Array of pet objects

#### GET /api/v3/pet/{petId}
Find pet by ID.

**Auth Required:** No

**Response:** Pet object

#### POST /api/v3/pet/{petId}
Update pet with form data.

**Auth Required:** Yes (store_owner, admin)

**Request Body:**
```json
{
  "name": "string",
  "status": "string"
}
```

**Response:**
```json
{
  "code": "number",
  "type": "string",
  "message": "string"
}
```

#### DELETE /api/v3/pet/{petId}
Delete a pet.

**Auth Required:** Yes (store_owner, admin)

**Response:** Status message

**Business Rules:**
- Cannot delete pets with active orders

#### POST /api/v3/pet/{petId}/uploadImage
Upload an image for a pet.

**Auth Required:** Yes (store_owner, admin)

**Request Body:** Multipart form data with file

**Response:** Status message

### Store

#### GET /api/v3/store/inventory
Get inventory counts by status.

**Auth Required:** Yes

**Response:**
```json
{
  "available": "number",
  "pending": "number",
  "sold": "number"
}
```

#### POST /api/v3/store/order
Place an order for a pet.

**Auth Required:** Yes (customer, store_owner, admin)

**Request Body:**
```json
{
  "petId": "number",
  "quantity": "number",
  "shipDate": "string",
  "status": "string",
  "complete": "boolean"
}
```

**Response:**
```json
{
  "id": "number",
  "petId": "number",
  "quantity": "number",
  "shipDate": "string",
  "status": "string",
  "complete": "boolean"
}
```

**Business Rules:**
- Pet must be available
- Quantity must be 1 for live animals
- Cannot order pets with existing active orders
- Ordering changes pet status to pending

#### GET /api/v3/store/order/{orderId}
Get order by ID.

**Auth Required:** Yes

**Response:** Order object

**Business Rules:**
- Customers can only view their own orders
- Store owners and admins can view all orders

#### PUT /api/v3/store/order/{orderId}
Update order status (store owner only).

**Auth Required:** Yes (store_owner, admin)

**Request Body:**
```json
{
  "status": "placed|approved|delivered"
}
```

**Response:** Updated order object

**Business Rules:**
- Cannot modify delivered orders
- Delivering order changes pet status to sold

#### DELETE /api/v3/store/order/{orderId}
Cancel an order.

**Auth Required:** Yes

**Response:** Status message

**Business Rules:**
- Customers can only cancel their own orders
- Can only cancel placed orders
- Canceling returns pet to available status

### Users

#### POST /api/v3/user
Create a new user.

**Auth Required:** No

**Request Body:**
```json
{
  "username": "string",
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "password": "string",
  "phone": "string",
  "userStatus": "number"
}
```

**Response:** Status message

#### POST /api/v3/user/createWithList
Create multiple users.

**Auth Required:** No

**Request Body:**
```json
{
  "users": [/* array of user objects */]
}
```

**Response:** Status message

#### GET /api/v3/user/login
User login.

**Auth Required:** No

**Query Parameters:**
- `username`: string
- `password`: string

**Response:**
```json
{
  "token": "string",
  "expires": "string"
}
```

#### GET /api/v3/user/logout
User logout.

**Auth Required:** Yes

**Response:** Status message

#### GET /api/v3/user/{username}
Get user by username.

**Auth Required:** Yes

**Response:** User object

**Business Rules:**
- Users can only view their own profile
- Admins can view any profile

#### PUT /api/v3/user/{username}
Update user.

**Auth Required:** Yes

**Request Body:**
```json
{
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "password": "string",
  "phone": "string",
  "userStatus": "number",
  "role": "string"
}
```

**Response:** Status message

**Business Rules:**
- Users can only edit their own profile
- Only admins can change user roles

#### DELETE /api/v3/user/{username}
Delete user.

**Auth Required:** Yes (admin only)

**Response:** Status message

**Business Rules:**
- Cannot delete users with active orders

## Error Responses

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (missing or invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

### Error Format

```json
{
  "error": "Error message",
  "code": "number",
  "type": "error"
}
```

## State Transitions

### Pet Status
- `available` → `pending` (when order is placed)
- `pending` → `sold` (when order is delivered)
- `pending` → `available` (when order is cancelled)
- `sold` → `available` (admin only)

### Order Status
- `placed` → `approved` (store owner approval)
- `approved` → `delivered` (order completion)
- `placed` → deleted (customer cancellation)

## Test Users

Default test users (password: "password"):

- `admin` - Full system access
- `storeowner` - Store management access
- `customer1` - Customer access
- `customer2` - Customer access