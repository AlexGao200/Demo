# User Routes API Documentation

## GET /api/v1/user/{user_id}/indices

Get user indices.

**Parameters:**
- `user_id` (path): The ID of the user

**Responses:**
- 200: User indices retrieved successfully
- 403: Unauthorized access
- 404: User not found

## POST /api/v1/user/{user_id}/join-organization

Join an organization.

**Parameters:**
- `user_id` (path): The ID of the user
- `org_id` (body): The ID of the organization to join
- `role` (body, optional): The role of the user in the organization (default: member)

**Responses:**
- 200: Successfully joined the organization
- 400: User is already a member of this organization
- 403: Unauthorized access
- 404: User or organization not found


## GET /api/v1/user/{user_id}/organizations

Get user organizations.

**Parameters:**
- `user_id` (path): The ID of the user

**Responses:**
- 200: User organizations retrieved successfully
- 403: Unauthorized access
- 404: User not found

## POST /api/v1/user/{user_id}/leave-organization

Leave an organization.

**Parameters:**
- `user_id` (path): The ID of the user
- `org_id` (body): The ID of the organization to leave

**Responses:**
- 200: Successfully left the organization
- 400: User is not a member of this organization
- 403: Unauthorized access
- 404: User or organization not found

## GET /api/v1/user/{user_id}/roles

Get user roles in organizations.

**Parameters:**
- `user_id` (path): The ID of the user

**Responses:**
- 200: User roles retrieved successfully
- 403: Unauthorized access
- 404: User not found

## POST /api/v1/user/{user_id}/token_limit

Set user token limit.

**Parameters:**
- `user_id` (path): The ID of the user
- `token_limit` (body): The new token limit for the user

**Responses:**
- 200: Token limit updated successfully
- 403: Unauthorized access
- 404: User not found
