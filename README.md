# 🌟 NormPlov Platform Introduction

**NormPlov** is an innovative platform designed to guide users, especially high school students, in making informed decisions about their academic and career paths. Using quizzes, data analytics, and machine learning, we provide personalized recommendations based on interests, skills, and learning styles. 

## 🌟 Main Features

1. **Quiz Assessment**  
   - Analyze learning style, values, interests, personality, and skills.
   - Provide detailed results with university majors, career paths, and more.
   - Help high school students align academic and career choices.

2. **Trending Market Jobs**  
   - Search and explore trending job markets.

3. **University Details**  
   - View popular majors, fee ranges, and available courses for each university.

4. **User Dashboard**  
   - Manage profile, test history, saved drafts, and other personalized features.

5. **AI Recommendations**  
   - Leverage AI to provide detailed insights into test results.

6. **Admin Management**  
   - Manage profiles, data visualization, user feedback, job listings, majors, universities, and scraping trending jobs.  
   - Promote user feedback to the UI and block/unblock users.

---

# 🚀 NormPlov API using FastAPI

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.78.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)

# 🚀 NormPlov API

The **NormPlov API** is a robust platform built with **FastAPI**, seamlessly integrating statistical models, machine learning techniques, and advanced data analytics to power the **NormPlov web application**. It is specifically designed to provide high school students with tailored career guidance, academic insights, and connections to trending job opportunities.

### **Authentication Endpoints**

1. 🔑 **Login**  
   - **Method:** `POST`  
   - **URL:** `/auth/login`  
   - **Description:** Authenticate users and provide access and refresh tokens.

2. ✍️ **Register**  
   - **Method:** `POST`  
   - **URL:** `/auth/register`  
   - **Description:** Create a new user account.

3. ✅ **Verify Email**  
   - **Method:** `POST`  
   - **URL:** `/auth/verify`  
   - **Description:** Verify a user's email with a verification code.

4. 🔁 **Resend Verification Code**  
   - **Method:** `POST`  
   - **URL:** `/auth/resend-verification-code`  
   - **Description:** Resend the email verification code.

5. 🔒 **Request Password Reset**  
   - **Method:** `POST`  
   - **URL:** `/auth/password-reset-request`  
   - **Description:** Request a password reset for a user.

6. 🔓 **Reset Password**  
   - **Method:** `POST`  
   - **URL:** `/auth/reset-password`  
   - **Description:** Reset the user's password with a reset code.

7. 🚪 **Logout**  
   - **Method:** `POST`  
   - **URL:** `/auth/logout`  
   - **Description:** Log the user out and invalidate the tokens.

8. ♻️ **Refresh Token**  
   - **Method:** `POST`  
   - **URL:** `/auth/refresh`  
   - **Description:** Refresh expired access tokens.

9. 🌐 **Login with Google**  
   - **Method:** `GET`  
   - **URL:** `/auth/google`  
   - **Description:** Redirect to Google login page.

10. 📥 **Google Login Callback**  
   - **Method:** `GET`  
   - **URL:** `/auth/google/callback`  
   - **Description:** Handle the callback after Google login.

11. 📧 **Resend Reset Password Email**  
   - **Method:** `POST`  
   - **URL:** `/auth/resend-reset-password`  
   - **Description:** Resend the password reset email.

12. 🔍 **Verify Reset Password Code**  
   - **Method:** `POST`  
   - **URL:** `/auth/verify-reset-password`  
   - **Description:** Verify the reset password code.

### **User Endpoints**

1. 🖼️ **Upload User Profile Picture**  
   - **Method:** `POST`  
   - **URL:** `{{normplov}}user/profile/upload/21c40132-a2c0-4bad-a098-766f350c98d6`  
   - **Description:** Upload a profile picture for the user.  
   - **Body:**  
     - `file` (type: `file`) - The profile picture file to upload.

2. ✏️ **Update User Profile**  
   - **Method:** `PUT`  
   - **URL:** `{{normplov}}user/profile/update/21c40132-a2c0-4bad-a098-766f350c98d6`  
   - **Description:** Update user profile details such as username, address, and bio.  
   - **Body:**  
     - `username` (string)  
     - `address` (string)  
     - `phone_number` (string)  
     - `bio` (string)  
     - `gender` (string)  
     - `date_of_birth` (string, ISO 8601 format)  

3. 🔒 **Change Password**  
   - **Method:** `POST`  
   - **URL:** `{{normplov}}user/change-password`  
   - **Description:** Change the user's password.  
   - **Body:**  
     - `old_password` (string)  
     - `new_password` (string)  
     - `confirm_new_password` (string)  

4. 📝 **Update User Bio**  
   - **Method:** `PUT`  
   - **URL:** `{{normplov}}user/bio`  
   - **Description:** Update the user's bio.  
   - **Body:**  
     - `bio` (string)  

5. 👤 **Get User Profile**  
   - **Method:** `GET`  
   - **URL:** `{{normplov}}user/me`  
   - **Description:** Retrieve the profile details of the currently authenticated user.  

6. 📧 **Load User by Email**  
   - **Method:** `GET`  
   - **URL:** `{{normplov}}user/email/lymannphy9@gmail.com`  
   - **Description:** Retrieve user details using their email address.  

7. 🔍 **Get User by UUID**  
   - **Method:** `GET`  
   - **URL:** `{{normplov}}user/retrieve/21c40132-a2c0-4bad-a098-766f350c98d6`  
   - **Description:** Retrieve user details using their UUID.  

### **Assessment Endpoints**

1. 🧠 **Learning Styles Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}assessment/predict-learning-style`
   - **Description:** Submit responses to predict the user's learning style.
   - **Body:**
     ```json
     {
       "responses": {
         "Q1_Visual": 1,
         "Q2_Visual": 1,
         "Q3_Auditory": 2,
         "Q4_Auditory": 1,
         "Q5_ReadWrite": 1,
         "Q6_ReadWrite": 3,
         "Q7_Kinesthetic": 1,
         "Q8_Kinesthetic": 1
       }
     }
     ```

2. 🔧 **Skill Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}assessment/predict-skills`
   - **Description:** Submit responses to predict the user's skill levels.
   - **Body:**
     ```json
     {
       "responses": {
         "Complex Problem Solving": 4.2,
         "Critical Thinking Score": 3.5,
         "Mathematics Score": 4.8,
         "Science Score": 3.2,
         "Learning Strategy Score": 3.9,
         "Monitoring Score": 4.1,
         "Active Listening Score": 4.0,
         "Social Perceptiveness Score": 2.5,
         "Judgment and Decision Making Score": 4.7,
         "Instructing Score": 3.0,
         "Active Learning Score": 3.8,
         "Time Management Score": 2.0,
         "Writing Score": 1.8,
         "Speaking Score": 4.6,
         "Reading Comprehension Score": 1.2
       }
     }
     ```

3. 🤖 **AI Recommendations**
   - **Method:** `POST`
   - **URL:** `{{normplov}}ai_recommendations`
   - **Description:** Submit a query to get AI-generated career recommendations.
   - **Body:**
     ```json
     {
       "query": "Based on my response, can you give me some recommendation just like giving me a career that is suitable for me please?"
     }
     ```

4. 🧑‍🤝‍🧑 **Personality Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}assessment/personality-assessment`
   - **Description:** Submit responses for personality analysis.
   - **Body:**
     ```json
     {
       "responses": {
         "Q1": 5, "Q2": 4, "Q3": 3, "Q4": 2, "Q5": 4,
         "Q6": 5, "Q7": 1, "Q8": 1, "Q9": 3, "Q10": 3,
         "Q11": 3, "Q12": 3, "Q13": 3, "Q14": 3, "Q15": 3,
         "Q16": 3
       }
     }
     ```

5. 🎯 **Interest Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}assessment/process-interest-assessment`
   - **Description:** Submit responses to assess the user's interests.
   - **Body:**
     ```json
     {
       "responses": {
         "Q1": 5, "Q2": 4, "Q3": 3, "Q4": 5, "Q5": 2,
         "Q6": 4, "Q7": 1, "Q8": 2, "Q9": 3, "Q10": 4,
         "Q11": 2, "Q12": 5
       }
     }
     ```

6. 🌟 **Value Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}assessment/process-value-assessment`
   - **Description:** Submit responses to assess the user's values.
   - **Body:**
     ```json
     {
       "responses": {
         "Q1": 1, "Q2": 4, "Q3": 3, "Q4": 2, "Q5": 5,
         "Q6": 3, "Q7": 4, "Q8": 1, "Q9": 2, "Q10": 3,
         "Q11": 4, "Q12": 2, "Q13": 5, "Q14": 1, "Q15": 4,
         "Q16": 3, "Q17": 3, "Q18": 4, "Q19": 5, "Q20": 2,
         "Q21": 3, "Q22": 4
       }
     }
     ```

### **Learning Style Image Endpoints**

1. 🖼️ **Upload Learning Style Image**
   - **Method:** `POST`
   - **URL:** `{{normplov}}learning-style-image/upload-learning-style-image`
   - **Description:** Upload an image associated with a specific learning style technique.
   - **Headers:**
     - `Content-Type` (default: `multipart/form-data`)
   - **Body:**
     - `technique_uuid` (type: `text`) - The unique identifier of the learning style technique.
     - `file` (type: `file`) - The image file to upload.

2. ✏️ **Update Learning Style Image**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}learning-style-image/update-learning-style-image/7d230fa9-5c6a-4a02-a578-6814f2207518`
   - **Description:** Update an existing learning style image by providing a new file.
   - **Body:**
     - `image_uuid` (type: `text`) - The unique identifier of the image to update.
     - `file` (type: `file`) - The new image file to upload.

3. ❌ **Delete Learning Style Image**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}learning-style-image/delete-learning-style-image`
   - **Description:** Delete a learning style image by its unique identifier. (Ensure to specify the `image_uuid` as a query parameter or in the request body.)

4. 📂 **Load All Learning Style Images**
   - **Method:** `GET`
   - **URL:** `{{normplov}}learning-style-image/load-all-learning-style-images`
   - **Description:** Retrieve a list of all uploaded learning style images.
   - **Headers:** None
   - **Body:** None

### **Draft Management Endpoints**

1. 📝 **Save Draft**
   - **Method:** `POST`
   - **URL:** `{{normplov}}draft/save-draft?assessment_name=Learning Style`
   - **Description:** Save a draft for an assessment, including the test UUID and response data.
   - **Body:**
     ```json
     {
       "test_uuid": "2a71d287-74b0-4fb1-8cdd-87aac7b62a1b",
       "response_data": {
         "Q1_Visual": 1,
         "Q2_Visual": 1,
         "Q3_Auditory": 2
       }
     }
     ```

2. 📂 **Load All Drafts**
   - **Method:** `GET`
   - **URL:** `{{normplov}}draft/load-drafts`
   - **Description:** Retrieve a list of all saved drafts.

3. 🔍 **Retrieve Draft by UUID**
   - **Method:** `GET`
   - **URL:** `{{normplov}}draft/retrieve-draft/273d5e63-7900-4794-a29e-564ecbe7546e`
   - **Description:** Retrieve a specific draft by its UUID.

4. 🚀 **Submit Draft Assessment**
   - **Method:** `POST`
   - **URL:** `{{normplov}}draft/submit-draft-assessment/2d751d20-0bda-48f1-a706-d4e507791768`
   - **Description:** Submit a saved draft for assessment processing.

5. ❌ **Delete Draft by UUID**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}draft/delete-draft-assessment/411707df-11f4-4174-b7b4-687b35b6df01`
   - **Description:** Delete a specific draft by its UUID.

### **Test Endpoints**

1. 🛠️ **Test Responses**
   - **Method:** `GET`
   - **URL:** `{{normplov}}test/responses?test_uuid=00f559a4-8c0e-40e1-bb2c-09e53c0a2daf`
   - **Description:** Retrieve responses for a specific test by its UUID.

2. 📋 **Load Test Details**
   - **Method:** `GET`
   - **URL:** `{{normplov}}test/get-test-details/00f559a4-8c0e-40e1-bb2c-09e53c0a2daf`
   - **Description:** Get the details of a specific test by its UUID.

3. 👤 **User Tests**
   - **Method:** `GET`
   - **URL:** `{{normplov}}test/user-tests`
   - **Description:** Retrieve a list of tests associated with the authenticated user.

4. ❌ **Delete Test**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}test/delete-test/ba2d2887-70b3-49fa-af89-32db462520a8`
   - **Description:** Delete a test by its UUID.

5. 🔗 **Generate Shareable Link**
   - **Method:** `GET`
   - **URL:** `{{normplov}}test/generate-shareable-link/00f559a4-8c0e-40e1-bb2c-09e53c0a2daf`
   - **Description:** Generate a shareable link for a specific test.

6. 📤 **Retrieve Shared Test**
   - **Method:** `GET`
   - **URL:** `{{normplov}}test/5fd9dcf4-3e34-472d-9cba-a889ac95d9c3/response`
   - **Description:** Retrieve a shared test's responses using its unique identifier.

---

### **User Feedback Endpoints**

1. 💬 **Create Feedback**
   - **Method:** `POST`
   - **URL:** `{{normplov}}feedback/create`
   - **Description:** Submit feedback for a specific assessment.
   - **Body:**
     ```json
     {
       "feedback": "I really enjoyed this assessment.",
       "assessment_type_uuid": "b813679b-5a83-4f86-8754-a385c499d6ad"
     }
     ```

2. 🌟 **Fetch All Promoted Feedback**
   - **Method:** `GET`
   - **URL:** `{{normplov}}feedback/promoted`
   - **Description:** Retrieve all feedback marked as promoted.
  
### **School Endpoints**

1. 📚 **Load School Majors**
   - **Method:** `GET`
   - **URL:** `{{normplov}}schools/6143d181-c0d2-48d9-a40c-dcd6794b286d/majors`
   - **Description:** Retrieve the majors offered by a specific school identified by its UUID.

2. 🏫 **Get All Schools**
   - **Method:** `GET`
   - **URL:** `{{normplov}}schools?province_uuid=1e9ab46c-acee-4d4a-b784-ad4c59b0e5de&page=1&page_size=10`
   - **Description:** Retrieve all schools with optional filters like province UUID, pagination, and page size.

---

### **Job Management Endpoints**

1. 🌍 **Load Provinces**
   - **Method:** `GET`
   - **URL:** `{{normplov}}jobs/provinces`
   - **Description:** Retrieve a list of provinces for job filtering or categorization.

2. 🏷️ **Load Job Types**
   - **Method:** `GET`
   - **URL:** `{{normplov}}jobs/job-types`
   - **Description:** Retrieve the types of jobs available, such as Full-time or Part-time.

3. 🗂️ **Load Job Categories**
   - **Method:** `GET`
   - **URL:** `{{normplov}}jobs/job-categories`
   - **Description:** Retrieve all job categories. 

4. 📄 **Load Jobs with Pagination**
   - **Method:** `GET`
   - **URL:** `{{normplov}}jobs?job_category_uuid=8fec9cb7-da9f-40fc-9adc-d0cd71bb4a73&province_uuid=1e9ab46c-acee-4d4a-b784-ad4c59b0e5de&job_type=Full-time`
   - **Description:** Retrieve a paginated list of jobs with optional filters such as job category UUID, province UUID, and job type.
   - **Note:** Example filter format:
     ```
// {{normplov}}jobs?job_category_uuid=123e4567-e89b-12d3-a456-426614174000&province_uuid=abcdef12-34ab-56cd-78ef-1234567890ab&job_type=Full-time
     ```

### **Admin Endpoints**

#### **User Management**
1. 🔒 **Block User**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}user/block/5be49f5f-e318-410c-969a-8497043a04fe`
   - **Description:** Block a specific user by their UUID.

2. 📋 **Load All Users**
   - **Method:** `GET`
   - **URL:** `{{normplov}}user/list`
   - **Description:** Retrieve a paginated list of users with optional filters and sorting.

3. ❌ **Delete User by UUID**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}delete/`
   - **Description:** Delete a user by their UUID.

---

#### **Job Management**
1. 📝 **Job Creation**
   - **Method:** `POST`
   - **URL:** `{{normplov}}jobs`
   - **Description:** Create a new job posting.
   - **Body:**
     ```json
     {
       "type": "Full-time",
       "position": "Software Engineer",
       "qualification": "Bachelor's degree",
       "published_date": "2024-12-05T12:00:00",
       "description": "Develop and maintain software solutions.",
       "responsibilities": "Write code, review code, deploy code.",
       "requirements": "3+ years of experience in software development.",
       "resources": "Online documentation and team collaboration tools.",
       "job_category_uuid": "8fec9cb7-da9f-40fc-9adc-d0cd71bb4a73",
       "province_uuid": "1e9ab46c-acee-4d4a-b784-ad4c59b0e5de",
       "company_uuid": "bdd8c942-cb96-4eee-9274-ad00b18aecff",
       "salaries": 200.00
     }
     ```

2. ✏️ **Update Job**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}jobs/00da49a2-3efb-4352-9ca3-aa0f2fe6f7f0`
   - **Description:** Update an existing job posting.
   - **Body:**
     ```json
     {
       "type": "Full-time",
       "position": "Software Engineer",
       "qualification": "Bachelor's degree in Computer Science",
       "published_date": "2024-12-05T12:00:00",
       "description": "Develop and maintain software applications.",
       "responsibilities": "Write, test, and deploy software solutions.",
       "requirements": "3+ years of software development experience.",
       "resources": "Online documentation, code repositories",
       "job_category_uuid": "8fec9cb7-da9f-40fc-9adc-d0cd71bb4a73",
       "salaries": 300.00
     }
     ```

3. ❌ **Delete Job by UUID**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}jobs/00da49a2-3efb-4352-9ca3-aa0f2fe6f7f0`
   - **Description:** Delete a job posting by UUID.

---

#### **Job Category Management**
1. 🏷️ **Create Job Category**
   - **Method:** `POST`
   - **URL:** `{{normplov}}job-categories`
   - **Description:** Create a new job category.
   - **Body:**
     ```json
     {
       "name": "Digital Marketing",
       "description": "Involves promoting products or services through digital platforms like social media, search engines, and email campaigns. Includes roles such as content creators, SEO specialists, and social media managers, requiring creativity and analytical thinking."
     }
     ```

2. 📋 **Get All Job Categories**
   - **Method:** `GET`
   - **URL:** `{{normplov}}job-categories`
   - **Description:** Retrieve all job categories.

3. ✏️ **Update Job Category**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}job-categories/1d64ff61-4b4c-45b8-9964-2f4f65b6441a`
   - **Description:** Update an existing job category.
   - **Body:**
     ```json
     {
       "name": "Data Science"
     }
     ```

4. ❌ **Delete Job Category**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}job-categories/1d64ff61-4b4c-45b8-9964-2f4f65b6441a`
   - **Description:** Delete a specific job category.

### **School Management Endpoints**

1. 🏫 **Create School**
   - **Method:** `POST`
   - **URL:** `{{normplov}}schools`
   - **Description:** Create a new school entry.
   - **Body:**
     ```json
     {
       "province_uuid": "1e9ab46c-acee-4d4a-b784-ad4c59b0e5de",
       "kh_name": "សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ",
       "en_name": "Royal University of Phnom Penh",
       "type": "PRIVATE",
       "logo_url": "https://example.com/logo.png",
       "cover_image": "https://example.com/cover.png",
       "location": "Phnom Penh",
       "phone": "012345678",
       "lowest_price": 1000.00,
       "highest_price": 3000.00,
       "map": "https://maps.google.com/?q=Phnom+Penh",
       "email": "info@school.com",
       "website": "https://school.com",
       "description": "A top-tier private school",
       "mission": "To educate the leaders of tomorrow",
       "vision": "To be the top school in the region"
     }
     ```

2. ❌ **Delete School**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}schools/6371aa4b-6297-4ea5-9a0f-d9a5da713953`
   - **Description:** Delete a specific school by its UUID.

3. ✏️ **Update School**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}schools/4c02af47-699c-4f68-8aea-7f6ce1dfb9c1`
   - **Description:** Update school details.
   - **Body:**
     ```json
     {
       "kh_name": "សាលារដ្ឋ",
       "en_name": "Public School"
     }
     ```

---

### **Major Management Endpoints**

1. 🎓 **Create Major**
   - **Method:** `POST`
   - **URL:** `{{normplov}}majors`
   - **Description:** Create a new major.
   - **Body:**
     ```json
     {
       "name": "Computer Science",
       "description": "Study of computation, algorithms, and systems.",
       "fee_per_year": 8000.00,
       "duration_years": 4,
       "degree": "Bachelor",
       "career_uuids": [
         "0eb87c92-1f3d-4f66-8561-b8d233b890ff",
         "48dd21b7-f64f-45eb-9605-2a0eb8481432"
       ],
       "school_uuids": [
         "6143d181-c0d2-48d9-a40c-dcd6794b286d",
         "a872a95e-129d-4bb8-bf07-a25ceb48d8da"
       ]
     }
     ```

2. 🔍 **Fetch Careers for Major**
   - **Method:** `GET`
   - **URL:** `{{normplov}}majors/89aaae81-0f55-42ba-918d-bf1bddb82024/careers`
   - **Description:** Retrieve careers associated with a specific major.

---

### **User Feedback Endpoints**

1. 💬 **Fetch All Feedback**
   - **Method:** `GET`
   - **URL:** `{{normplov}}feedback/all`
   - **Description:** Retrieve all user feedback.

2. 🌟 **Promote Feedback**
   - **Method:** `POST`
   - **URL:** `{{normplov}}feedback/promote/8d9fb6fb-a432-41ee-8e2b-8c4892398d83`
   - **Description:** Promote a specific feedback entry.

---

### **Faculty Management Endpoints**

1. 🏫 **Create Faculty**
   - **Method:** `POST`
   - **URL:** `{{normplov}}faculties`
   - **Description:** Create a new faculty under a school.
   - **Body:**
     ```json
     {
       "name": "Faculty of Science",
       "description": "The Faculty of Science is dedicated to advancing knowledge and fostering innovation in natural and physical sciences.",
       "school_uuid": "4c02af47-699c-4f68-8aea-7f6ce1dfb9c1"
     }
     ```

2. 📋 **Load All Faculties**
   - **Method:** `GET`
   - **URL:** `{{normplov}}faculties`
   - **Description:** Retrieve all faculties.

3. ❌ **Delete Faculty**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}faculties/ab4fea73-18d0-4b63-8cdb-f7f08c3ec70f`
   - **Description:** Delete a specific faculty by its UUID.

4. ✏️ **Update Faculty**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}faculties/70e7bbcd-ad8a-4287-bb74-4c7cdb2b304d`
   - **Description:** Update faculty details.
   - **Body:**
     ```json
     {
       "name": "Faculty of Science"
     }
     ```

---

### **Company Management Endpoints**

1. 🏢 **Create Company**
   - **Method:** `POST`
   - **URL:** `{{normplov}}companies`
   - **Description:** Create a new company entry.
   - **Body:**
     ```json
     {
       "name": "Mazer Company",
       "address": "1234 Company St, Mazer City, Mazer Country",
       "linkedin": "https://www.linkedin.com/company/awesome-company",
       "twitter": "https://twitter.com/mazer_company",
       "facebook": "https://www.facebook.com/mazer_company",
       "instagram": "https://www.instagram.com/mazer_company",
       "website": "https://www.mazercompany.com"
     }
     ```

2. 🖼️ **Upload Company Logo**
   - **Method:** `POST`
   - **URL:** `{{normplov}}companies/upload-logo/993de624-6da4-4745-9ce5-3ecc2aaa3403`
   - **Description:** Upload a company logo.
   - **Body:**
     - `file` (type: `file`) - The logo file to upload.

3. ✏️ **Update Company**
   - **Method:** `PUT`
   - **URL:** `{{normplov}}companies/ac32e0af-4b89-4db8-adb9-b4879fd9a784`
   - **Description:** Update company details.
   - **Body:**
     ```json
     {
       "name": "Mazer Company, Hasha"
     }
     ```

4. ❌ **Delete Company**
   - **Method:** `DELETE`
   - **URL:** `{{normplov}}companies`
   - **Description:** Delete a company entry.

5. 📋 **Retrieve Companies**
   - **Method:** `GET`
   - **URL:** `{{normplov}}companies`
   - **Description:** Retrieve all companies.


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

    ### 🛠️ Technologies Used
- **Python 3.9+**
- **FastAPI 0.78.0**

---

### 🎉 Acknowledgements

We would like to express our deepest appreciation to:

- **Mr. Chen Phirum**, the director of the Institute of Science and Technology Advanced Development, who has provided invaluable guidance and support for our NormPlov website project. His mentorship, leadership, and effective problem-solving have been instrumental in completing this initiative.  
- **Ms. Mom Reksmey** and **Mr. Ing Muyleang**, our exceptional mentors, for their inspiring suggestions and coordination, which helped us successfully implement and refine this project.

✨ **Thank you for making this project possible!** ✨  

---

### 🙌 Contributors
- 👩‍💻 **Hout Sovannarith**  
- 👨‍💻 **Yeng SokRoza**  
- 👩‍💻 **Chhem Chhunhy**
- 👩‍💻 **Chantha Seamey**
- 👩‍💻 **Chhoeurn Kimla**
- 👩‍💻 **Phy Lymann**  

---

### 📬 Contact
- **Email**: support@normplov.com  
- **Website**: [NormPlov](https://normplov.com)  

---

🎉 _NormPlov API — Empowering Education Through Technology!_ 🎉
    ```

---


