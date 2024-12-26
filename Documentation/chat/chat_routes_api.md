# Chat Routes API Documentation

This document provides detailed information about the chat-related API endpoints for frontend engineers. These endpoints are defined in the `chat_routes.py` file and handle various chat functionalities such as creating chats, retrieving chat history, and processing user queries.

## Base URL

All endpoints are relative to the base URL of the API server.

## Authentication

All endpoints require authentication using a JWT token. The token should be included in the `Authorization` header of each request as a Bearer token.

Example:
```
Authorization: Bearer <your_jwt_token>
```

## Input Validation

Many endpoints use the `@validate_input` decorator to ensure required parameters are present in the request. If a required parameter is missing, the API will return a 400 Bad Request error.

## Endpoints

### 1. Get Chat History

Retrieves the chat history for a specific chat.

- **URL:** `/api/chat_history`
- **Method:** GET
- **URL Params:**
  - Required: `chat_id=[string]`

#### Success Response

- **Code:** 200
- **Content:**
```json
[
    {
        "sender": "user" | "ai",
        "content": string,
        "timestamp": "ISO 8601 formatted string",
        "cited_sections": [
            {
                "preview": string,
                "title": string,
                "document_id": string,
                "pages": [int],
                "extra_data": object
            }
        ]
    },
    ...
]
```

#### Error Responses

- **Code:** 400 BAD REQUEST
  - **Content:** `{ "error": "Chat ID is required" }`
- **Code:** 404 NOT FOUND
  - **Content:** `{ "error": "Chat not found" }`
- **Code:** 500 INTERNAL SERVER ERROR
  - **Content:** `{ "error": "Error fetching chat history" }`

### 2. Create Chat

Creates a new chat session for the authenticated user.

- **URL:** `/api/chat`
- **Method:** POST
- **Data Params:**
```json
{
    "time_zone": string (e.g., "UTC", "America/New_York")
}
```

#### Success Response

- **Code:** 201 CREATED
- **Content:**
```json
{
    "chat_id": string,
    "title": string
}
```

#### Error Responses

- **Code:** 400 BAD REQUEST
  - **Content:** `{ "error": "Time zone is required" }`
- **Code:** 500 INTERNAL SERVER ERROR
  - **Content:** `{ "error": "Error creating chat" }`

Note: When the first message is added to a chat, a `generate_chat_title` function is called to create a title based on the initial query.

### 3. Ask Question (Streaming)

Processes a user's question and streams the AI's response.

- **URL:** `/api/ask_stream`
- **Method:** POST
- **Data Params:**
```json
{
    "query": string,
    "chat_id": string,
    "indices": [string] (optional),
    "filter_dimensions": object (optional)
}
```

#### Success Response

- **Code:** 200
- **Content:** Server-Sent Events (SSE) stream with the following possible event types:

1. Content chunk:
```json
data: {"type": "content", "content": string}
```

2. Citations chunk:
```json
data: {
    "type": "citations",
    "data": {
        "cited_sections": [string],  // Array of JSON strings, each representing a cited section
        "full_text": string
    }
}
```

3. Error chunk:
```json
data: {"type": "error", "message": string}
```

4. Done event:
```json
data: {"type": "done"}
```

Each string in the `cited_sections` array is a JSON-encoded object with the following structure:
```json
{
    "preview": string,
    "title": string,
    "document_id": string,
    "pages": [int],
    "extra_data": object
}
```

Note: The frontend needs to parse the JSON strings in `cited_sections` to access the structured data.

#### Error Responses

- **Code:** 400 BAD REQUEST
  - **Content:** `{ "error": "Query and chat_id are required" }`
- **Code:** 402 PAYMENT REQUIRED
  - **Content:** `{ "error": "User is out of messages" }`
- **Code:** 500 INTERNAL SERVER ERROR
  - **Content:** `{ "error": "Error processing question" }`

Note: This endpoint checks the user's message limit before processing the query. If the user has reached their limit, a 402 error is returned.

### 4. Get Chat Sessions

Retrieves all chat sessions for the authenticated user.

- **URL:** `/api/chat_sessions`
- **Method:** GET

#### Success Response

- **Code:** 200
- **Content:**
```json
[
    {
        "id": string,
        "title": string,
        "createdAt": "ISO 8601 formatted string"
    },
    ...
]
```

#### Error Response

- **Code:** 500 INTERNAL SERVER ERROR
  - **Content:** `{ "error": "Error fetching chat sessions" }`

### 5. Get Specific Chat

Retrieves a specific chat for the authenticated user.

- **URL:** `/api/chat/:chat_id`
- **Method:** GET
- **URL Params:**
  - Required: `chat_id=[string]`

#### Success Response

- **Code:** 200
- **Content:**
```json
{
    "id": string,
    "title": string,
    "createdAt": "ISO 8601 formatted string",
    "messages": [
        {
            "sender": "user" | "ai",
            "content": string,
            "timestamp": "ISO 8601 formatted string",
            "cited_sections": [
                {
                    "preview": string,
                    "title": string,
                    "document_id": string,
                    "pages": [int],
                    "extra_data": object
                }
            ]
        },
        ...
    ]
}
```

#### Error Responses

- **Code:** 403 FORBIDDEN
  - **Content:** `{ "error": "Invalid token. User ID or fingerprint is required." }`
- **Code:** 404 NOT FOUND
  - **Content:** `{ "error": "User not found" }` or `{ "error": "Chat not found" }`
- **Code:** 500 INTERNAL SERVER ERROR
  - **Content:** `{ "error": "Error fetching chat" }`

## Rate Limiting

The `/api/ask_stream` endpoint is rate-limited to 10 requests per minute per user. This is implemented using the `limiter` object passed to the `create_chat_blueprint` function.

## Error Handling

All endpoints use a consistent error response format:

```json
{
    "error": "Description of the error"
}
```

The HTTP status code will indicate the type of error (e.g., 400 for client errors, 500 for server errors).

## Notes for Frontend Implementation

1. For the streaming endpoint (`/api/ask_stream`), use Server-Sent Events (SSE) to handle the real-time response. You'll need to parse each event and update the UI accordingly based on the event type (content, citations, error, or done).

2. All timestamps are in ISO 8601 format. Make sure to parse and display them correctly in the user's local time zone.

3. The `cited_sections` array in responses contains information about the sources used to generate the AI's response. You may want to display this information alongside the chat messages or provide a way for users to access it. Remember to parse the JSON strings in `cited_sections` to access the structured data.

4. Handle rate limiting gracefully by informing the user when they've reached the limit and when they can try again.

5. Implement proper error handling and display user-friendly error messages based on the error responses from the API.

6. For creating new chats, you may want to use the user's current time zone if available, or fall back to UTC.

7. When displaying chat sessions, sort them by the `createdAt` timestamp to show the most recent chats first.

8. Implement proper token management, including token refresh mechanisms, to ensure smooth user experience across long sessions.

9. Be prepared to handle the user message limit error (402) in the Ask Question endpoint and provide appropriate feedback to the user.

By following this documentation, you should be able to integrate the chat functionality into your frontend application effectively. If you encounter any issues or need further clarification, please don't hesitate to reach out to the backend team.
