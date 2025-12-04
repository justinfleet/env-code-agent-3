# Swagger Petstore API Documentation

## Overview
This is the Swagger Petstore API implementation with full JWT authentication, role-based access control, and business rule enforcement.

**Base URL**: `http://localhost:3002/api/v3`

## Authentication
Most endpoints require JWT authentication. Get a token by logging in first.

### Login
```http
GET /api/v3/user/login?username=customer&password=customer123
```

Use the returned token in the `Authorization: Bearer <token>` header for authenticated requests.

## User Roles
- **guest**: Unauthenticated users (can browse pets and inventory)
- **customer**: Registered users (can place orders, manage profile)
- **store_owner**: Store employees (can manage pets and orders)
- **admin**: System administrators (full access)

## Endpoints

### Pet Management

#### Get Pet by ID
- **GET** `/api/v3/pet/{petId}`
- **Auth**: Not required
- **Description**: Find pet by ID
- **Response**: Pet object with category and tags

#### Find Pets by Status  
- **GET** `/api/v3/pet/findByStatus?status={status}`
- **Auth**: Required (Bearer token)
- **Parameters**: 
  - `status`: available, pending, sold
- **Response**: Array of pets matching the status

#### Find Pets by Tags
- **GET** `/api/v3/pet/findByTags?tags={tags}`
- **Auth**: Required (Bearer token)
- **Parameters**:
  - `tags`: Comma-separated tag names
- **Response**: Array of pets with matching tags

#### Add New Pet
- **POST** `/api/v3/pet`
- **Auth**: Required (store_owner, admin roles only)
- **Body**: Pet object
- **Response**: Created pet object

#### Update Pet
- **PUT** `/api/v3/pet`
- **Auth**: Required (store_owner, admin roles only)
- **Body**: Pet object with ID
- **Response**: Updated pet object
- **Business Rule**: Only admin can change sold pets back to available

#### Update Pet with Form Data
- **POST** `/api/v3/pet/{petId}`
- **Auth**: Required (store_owner, admin roles only)
- **Body**: Form data (name, status)
- **Response**: Success message

#### Delete Pet
- **DELETE** `/api/v3/pet/{petId}`
- **Auth**: Required (store_owner, admin roles only)
- **Response**: Success message
- **Business Rule**: Cannot delete pets with active orders

#### Upload Pet Image
- **POST** `/api/v3/pet/{petId}/uploadImage`
- **Auth**: Required (store_owner, admin roles only)
- **Body**: Multipart form with file
- **Response**: Upload confirmation

### Store Operations

#### Get Store Inventory
- **GET** `/api/v3/store/inventory`
- **Auth**: Not required
- **Response**: Object with status counts (available: 2, pending: 1, sold: 1)

#### Place Order
- **POST** `/api/v3/store/order`
- **Auth**: Required (customer+ roles)
- **Body**: Order object
- **Response**: Created order
- **Business Rules**:
  - Pet must be available
  - Quantity must be 1 for live animals
  - Pet cannot have existing active orders
  - Changes pet status to "pending"

#### Get Order by ID
- **GET** `/api/v3/store/order/{orderId}`
- **Auth**: Required (ownership check)
- **Response**: Order object
- **Business Rule**: Users can only view their own orders (store_owner/admin can view all)

#### Cancel Order
- **DELETE** `/api/v3/store/order/{orderId}`
- **Auth**: Required (ownership check)
- **Response**: Success message
- **Business Rules**:
  - Can only cancel orders with "placed" status
  - Cannot cancel delivered orders
  - Returns pet to "available" status
  - Users can only cancel their own orders

### User Management

#### User Login
- **GET** `/api/v3/user/login?username={username}&password={password}`
- **Auth**: Not required
- **Response**: JWT token
- **Sample Users**:
  - admin/admin123 (admin role)
  - store_owner/store123 (store_owner role)  
  - customer/customer123 (customer role)

#### User Logout
- **GET** `/api/v3/user/logout`
- **Auth**: Not required
- **Response**: Success message

#### Get User
- **GET** `/api/v3/user/{username}`
- **Auth**: Required (ownership check)
- **Response**: User profile
- **Business Rule**: Users can only view their own profile (admin can view all)

#### Create User (Register)
- **POST** `/api/v3/user`
- **Auth**: Not required
- **Body**: User object
- **Response**: Success message
- **Note**: New users get "customer" role by default

#### Create Users (Bulk)
- **POST** `/api/v3/user/createWithList`
- **Auth**: Required (admin only)
- **Body**: Array of user objects
- **Response**: Success message

#### Update User
- **PUT** `/api/v3/user/{username}`
- **Auth**: Required (ownership check)
- **Body**: User object
- **Response**: Success message
- **Business Rules**:
  - Users can only update their own profile
  - Only admin can change user roles

#### Delete User
- **DELETE** `/api/v3/user/{username}`
- **Auth**: Required (admin only)
- **Response**: Success message
- **Business Rule**: Cannot delete users with active orders

## State Transitions

The API enforces these automatic state changes:

1. **Place Order**: Pet status changes from "available" → "pending"
2. **Cancel Order**: Pet status changes from "pending" → "available" (if order was "placed")
3. **Deliver Order**: Pet status changes to "sold" (when order status becomes "delivered")

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- **400**: Bad Request (validation errors, business rule violations)
- **401**: Unauthorized (missing or invalid token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found (resource doesn't exist)
- **409**: Conflict (duplicate username)
- **500**: Internal Server Error

## Sample Requests

### Login and Get Token
```bash
curl "http://localhost:3002/api/v3/user/login?username=customer&password=customer123"
```

### Find Available Pets
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:3002/api/v3/pet/findByStatus?status=available"
```

### Place Order
```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"petId": 1, "quantity": 1}' \
  "http://localhost:3002/api/v3/store/order"
```