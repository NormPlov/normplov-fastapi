# 🚀 FastAPI Authentication API

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.78.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)

This FastAPI project implements user authentication and authorization with features such as registration, login, password reset, and token refresh. It is built with FastAPI, and follows the OAuth2 authentication flow using JWT tokens for secure access to protected routes.

## 🔧 Key Features

- 🏷️ **JWT Authentication (OAuth2)**
- 🛡️ **Password Hashing** with `passlib`
- 🔑 **Access & Refresh Tokens**
- 📧 **Email Verification**
- 🔄 **Password Reset**
- 🔒 **Token-based user authentication**

## 🛠️ Routes and Endpoints

### 1. **Get Current User**
- **Method:** `GET`
- **URL:** `/user/me`
- **Description:** Retrieve the current logged-in user's details. This route requires a valid JWT token in the `Authorization` header.

### 2. **Refresh Token**
- **Method:** `POST`
- **URL:** `/auth/refresh`
- **Description:** Request a new access token using the refresh token.

### 3. **User Registration**
- **Method:** `POST`
- **URL:** `/auth/register`
- **Description:** Register a new user by providing details like email and password.

### 4. **Verify Email**
- **Method:** `POST`
- **URL:** `/auth/verify`
- **Description:** Verify the user's email using a code sent via email.

### 5. **Login**
- **Method:** `POST`
- **URL:** `/auth/login`
- **Description:** Authenticate the user with their email and password to receive an access token and refresh token.

### 6. **Forgot Password**
- **Method:** `POST`
- **URL:** `/auth/forgot-password`
- **Description:** Send a password reset link/code to the user's email.

### 7. **Reset Password**
- **Method:** `POST`
- **URL:** `/auth/reset-password`
- **Description:** Reset the password using the code received via email.

### 8. **Change Password**
- **Method:** `PUT`
- **URL:** `/auth/change-password`
- **Description:** Change the user's password by providing the old and new passwords.

## 🍀 Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone https://gitlab.com/spring-boot2905016/testing_auth_with_fast_api.git
   cd fast-api-python

## 🪄 Installation and Setup

1. **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate    # On Linux/macOS
    venv\Scripts\activate       # On Windows
    ```

2. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the FastAPI application:**

    ```bash
    uvicorn main:app --reload
    ```

---


