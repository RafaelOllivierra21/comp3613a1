# InternBridge API Specification

## Conventions

The InternBridge REST API exposes the five A1 workflows as JSON routes under `/api`, following the API specification format from Tutorials 4 and 5. The spec also serves as the API test plan for the Postman collection.

- **Base path:** every route starts with `/api`.
- **Authentication:** call `POST /api/auth` to get a token, then send `Authorization: Bearer <token>` on every protected route. The existing cookie login used by the HTML pages keeps working.
- **Success bodies:** `{"message": <string>}`, plus the new record's ID when one is created.
- **Error bodies:** `{"error": <string>}`.
- **Roles:** the role in brackets in each Description is the only role allowed to call that route.

| Status | Meaning |
| --- | --- |
| 200 | Data returned, or login succeeded |
| 201 | Record created or updated |
| 400 | Invalid value, or a business rule was broken |
| 401 | No token provided |
| 403 | Token belongs to a role that may not call the route |
| 404 | The ID in the URL or body does not exist |
| 422 | A required field is missing or has the wrong type (FastAPI validation) |

## API Specification

Thirteen routes cover account creation, login, the three named workflows and the two supporting workflows; every protected route has at least one negative case.

| Description | Method | URL | Request Headers, Body | Response Body, Status |
| --- | --- | --- | --- | --- |
| Create account | POST | `/api/signup` | `{"username": <string>, "password": <string>, "fullName": <string>, "email": <string>, "number": <string>}` | Success `{"message": "account created"}`, 201 |
|  |  |  |  | Bad Username or Email `{"error": "username or email already taken"}`, 400 |
|  |  |  |  | Missing Field `{"error": "invalid request body"}`, 422 |
| Login | POST | `/api/auth` | `{"username": <string>, "password": <string>}` | Success `{"token": <token>}`, 200 |
|  |  |  |  | Bad Credentials `{"error": "invalid credentials"}`, 400 |
| (Student) Apply for Internship | POST | `/api/applications` | `Authorization: Bearer <token>` | Success `{"message": "application submitted", "applicationID": <id>}`, 201 |
|  |  |  | `{"studentID": <int>, "gpa": <float>, "degreeName": <string>, "expectedGraduationDate": <YYYY-MM-DD>, "resumeLink": <url>, "skillIDs": [<int>]}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not a Student `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad Input (GPA, resume link, date or no skills) `{"error": "<field> is invalid"}`, 400 |
|  |  |  |  | Already Applied `{"error": "you have already applied for this cycle"}`, 400 |
|  |  |  |  | Bad Student ID `{"error": "student ID <studentID> already taken"}`, 400 |
|  |  |  |  | Cycle Closed `{"error": "applications are closed for this cycle"}`, 400 |
| (Student) View Own Application | GET | `/api/applications/me` | `Authorization: Bearer <token>` | Success `{"applicationID": <id>, "studentID": <int>, "status": <status>, "dateSubmitted": <date>, "student": {"fullName": <string>, "email": <string>, "number": <string>, "degreeName": <string>, "gpa": <float>, "expectedGraduationDate": <date>, "resumeLink": <url>}, "skills": [{"skillID": <id>, "name": <string>}], "matches": [{"matchID": <id>, "positionID": <id>, "title": <string>, "company": <string>, "status": <status>, "matchDate": <date>}]}`, 200 |
|  |  |  |  | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not a Student `{"error": "not authorized"}`, 403 |
|  |  |  |  | No Application `{"error": "no application found"}`, 404 |
| (Coordinator) List Applications | GET | `/api/applications` | `Authorization: Bearer <token>` | Success `[{"applicationID": <id>, "studentID": <int>, "fullName": <string>, "degreeName": <string>, "gpa": <float>, "status": <status>, "activeMatches": <int>}]`, 200 |
|  |  |  | `?status=< submitted / matched / awaiting rematch / placed / not matched >` (optional) | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the Coordinator `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad Status `{"error": "<status> not a valid status"}`, 400 |
| (Coordinator) View Suggested Positions | GET | `/api/applications/<applicationID>/suggestions` | `Authorization: Bearer <token>` | Success `[{"positionID": <id>, "title": <string>, "company": <string>, "fitPercent": <int>, "matchedSkills": [<string>], "missingSkills": [<string>]}]`, 200 (top 3 above 0% by default; every open position the student can still be matched to when `all=true`; `[]` when none) |
|  |  |  | `?all=true` (optional) | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the Coordinator `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad id `{"error": "application <applicationID> not found"}`, 404 |
| (Coordinator) Match Student to Position | POST | `/api/matches` | `Authorization: Bearer <token>` | Success `{"message": "match created", "matchID": <id>}`, 201 |
|  |  |  | `{"applicationID": <id>, "positionID": <id>}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the Coordinator `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad id `{"error": "application <applicationID> not found"}` or `{"error": "position <positionID> not found"}`, 404 |
|  |  |  |  | Rule Broken (cycle closed, application placed, position not open, pair already matched) `{"error": <reason>}`, 400 |
| (Company Rep) View Positions and Candidates | GET | `/api/positions/mine` | `Authorization: Bearer <token>` | Success `[{"positionID": <id>, "title": <string>, "status": <status>, "dateOpened": <date>, "candidates": [{"matchID": <id>, "fullName": <string>, "degreeName": <string>, "gpa": <float>, "email": <string>, "number": <string>, "resumeLink": <url>, "status": <status>}]}]`, 200 |
|  |  |  |  | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not a Company Rep `{"error": "not authorized"}`, 403 |
| (Company Rep) Update Candidate | PUT | `/api/matches/<matchID>` | `Authorization: Bearer <token>` | Success `{"message": "match updated", "status": <status>}`, 201 |
|  |  |  | `{"status": < "interviewing" / "offered" / "rejected by company" >}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not a Company Rep, or match belongs to another company `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad id `{"error": "match <matchID> not found"}`, 404 |
|  |  |  |  | Bad Status `{"error": "<status> not a valid status"}`, 400 |
|  |  |  |  | Not Allowed (offer before interviewing, offer already pending on the position, match closed) `{"error": <reason>}`, 400 |
| (Student) Respond to Offer | PUT | `/api/matches/<matchID>` | `Authorization: Bearer <token>` | Success `{"message": "match updated", "status": <status>}`, 201 |
|  |  |  | `{"status": < "accepted" / "declined by student" >}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the student's own match `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad id `{"error": "match <matchID> not found"}`, 404 |
|  |  |  |  | Bad Status `{"error": "<status> not a valid status"}`, 400 |
|  |  |  |  | No Pending Offer `{"error": "match has no pending offer"}`, 400 |
| (Company Rep) Post Open Position | POST | `/api/positions` | `Authorization: Bearer <token>` | Success `{"message": "position created", "positionID": <id>}`, 201 |
|  |  |  | `{"title": <string>, "description": <string>, "skillIDs": [<int>]}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not a Company Rep `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad Input (blank title or description, no skills, unknown skill ID) `{"error": "<field> is invalid"}`, 400 |
|  |  |  |  | Cycle Closed `{"error": "internship cycle is closed"}`, 400 |
| (Coordinator) Close Internship Cycle | PUT | `/api/cycles/<cycleID>` | `Authorization: Bearer <token>` | Success `{"message": "cycle closed", "applicationsNotMatched": <int>}`, 201 |
|  |  |  | `{"status": "closed"}` | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the Coordinator `{"error": "not authorized"}`, 403 |
|  |  |  |  | Bad id `{"error": "cycle <cycleID> not found"}`, 404 |
|  |  |  |  | Bad Status `{"error": "<status> not a valid status"}`, 400 |
|  |  |  |  | Already Closed `{"error": "cycle is already closed"}`, 400 |
| (Coordinator) List Users | GET | `/api/users` | `Authorization: Bearer <token>` | Success `[{"id": <id>, "username": <string>, "email": <string>}]`, 200 |
|  |  |  |  | When token not provided `{"error": "not authenticated"}`, 401 |
|  |  |  |  | Not the Coordinator `{"error": "not authorized"}`, 403 |

Accepting an offer also fills the position, places the application and closes the student's other matches and the other candidates' matches for that position, as in A1.