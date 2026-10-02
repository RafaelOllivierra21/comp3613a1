# COMP 3613 Assignment 1

Draft this file with the Guide. **Update it after every phase milestone** before you pause. The use-case diagram is a UML PNG at `docs/diagrams/use-case.png`, linked from this file as `diagrams/use-case.png` (path relative to `docs/report.md`). The model diagram is Mermaid. **Embed wireframe images** as `wireframes/<file>` (files live in `docs/wireframes/`).

Do not put your student ID in this file if you will commit it. The PDF cover adds your name and ID at export time.

## Assigned project

Internship Platform

## Three workflows

### 1.

Internship application (student)

### 2.

Student matching (coordinator)

### 3.

Candidate selection (company rep)

## Use case diagram

![Use case diagram](diagrams/use-case.png)

Phase 2 decisions: Students apply to the general internship program, not to a specific position. Student Matching includes viewing prescreened suggestions when the coordinator opens the matching screen; suggestions are limited to open positions and students not yet placed at a company, and a declined position is not suggested to that student again. The coordinator makes final position matches within Student Matching. Students can track their applications and matches; the coordinator can close the internship cycle; Company Reps can post open positions. Candidate Selection includes viewing matched students and is shared by the Company Rep and Student: the student's acceptance or decline completes the use case. Offering a position, moving a student to an external interview process, and rejecting a student are extensions of Candidate Selection. Student Matching occurs before Candidate Selection, but they remain independent use cases with no include/extend relationship between them.

## Model diagram

First draft. Update this section in Phase 5 when polish revises the model, and note what changed.

```mermaid
erDiagram
    User ||--o| Student : account
    User ||--o| Coordinator : account
    User ||--o| CompanyRep : account

    Company ||--o{ CompanyRep : employs
    Company ||--o{ Position : offers
    InternshipCycle ||--o{ Position : runs
    InternshipCycle ||--o{ Application : accepts

    Student ||--o{ Application : submits
    Application ||--o{ Match : leads_to
    Position ||--o{ Match : matches

    Student ||--o{ StudentSkill : has
    Skill ||--o{ StudentSkill : tags
    Position ||--o{ PositionSkill : requires
    Skill ||--o{ PositionSkill : defines

    User {
      int id PK
      string username
      string password
      string fullName
      string number
      string email
      string role
    }

    Student {
      int studentID PK
      int userID FK
      double gpa
      string degreeName
      date expectedGraduationDate
      string resumeLink
    }

    Coordinator {
      int coordinatorID PK
      int userID FK
    }

    CompanyRep {
      int repID PK
      int userID FK
      int companyID FK
    }

    Company {
      int companyID PK
      string name
      string location
    }

    Position {
      int positionID PK
      int companyID FK
      int cycleID FK
      string title
      string description
      date dateOpened
      string status
    }

    InternshipCycle {
      int cycleID PK
      date startDate
      date endDate
      string status
    }

    Application {
      int applicationID PK
      int studentID FK
      int cycleID FK
      date dateSubmitted
      string status
    }

    Match {
      int matchID PK
      int applicationID FK
      int positionID FK
      date matchDate
      string status
    }

    Skill {
      int skillID PK
      string name
    }

    StudentSkill {
      int studentID PK, FK
      int skillID PK, FK
    }

    PositionSkill {
      int positionID PK, FK
      int skillID PK, FK
    }
```

Assumptions: the internship program runs only at the UWI St. Augustine campus and is open to students across all faculties; resumes are stored as a link rather than an uploaded file. Positions belong to the company and are tied to an internship cycle, so closing a cycle can close the related positions. The `Match` record remains separate from `Application` to track interviews, offers, and outcome states without losing the original application record.

Phase 4 model review: the matching wireframe displays a fit percentage for suggested positions. This score will be calculated when suggestions are shown rather than stored on `Match`; no new model field is needed.

## Wireframes

The five wireframes cover all use cases in the Phase 2 diagram. Profile details and skills, application and cycle states, position details, and match outcomes shown in the designs are represented by the existing model fields. Match-fit percentages are calculated when suggestions are shown rather than persisted. Position candidate counts and active-match counts are display values derived from related records.

### Internship Application

![Internship Application](wireframes/internship_application.png)

### Student Matching

![Student Matching](wireframes/student_matching.png)

### Candidate Selection

![Candidate Selection](wireframes/candidate_selection.png)

### Post Open Positions

![Post Open Positions](wireframes/post_position.png)

### Close Internship Cycle

![Close Internship Cycle](wireframes/close_cycle.png)

<!-- student-build:wireframe-coverage
use_case: Internship Application
image: docs/wireframes/internship_application.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Student Matching
image: docs/wireframes/student_matching.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: View Prescreened Matches
image: docs/wireframes/student_matching.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Track Applications and Matches
image: docs/wireframes/candidate_selection.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Close Internship Cycle
image: docs/wireframes/close_cycle.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Post Open Positions
image: docs/wireframes/post_position.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Candidate Selection
image: docs/wireframes/candidate_selection.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: View Matched Students
image: docs/wireframes/candidate_selection.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Offer Position to Student
image: docs/wireframes/candidate_selection.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Move Student to External Interview Process
image: docs/wireframes/candidate_selection.png
covered: yes
-->

<!-- student-build:wireframe-coverage
use_case: Reject Student
image: docs/wireframes/candidate_selection.png
covered: yes
-->

`python manage.py report` also embeds any PNG/JPG still missing from `docs/wireframes/`.

## Theming

InternBridge uses a modern, professional visual identity. The main color is dark teal (`#172D36`), with mint (`#C3E8CF`) for filled accents and card borders, dark green for links, off-white (`#F7F7F2`) page backgrounds, white (`#FFFFFF`) cards, and muted grey (`#566A6F`) for small text. Manrope is loaded from Google Fonts. The light logo is used on the landing, login, and registration pages; the primary logo is used in the authenticated dark-teal navigation, and the InternBridge favicon is set site-wide. Logos appear without background boxes. Landing-page sign-in buttons use a dark-teal fill; signed-in landing actions use dark-teal-filled buttons as well. The browser title is InternBridge; the landing page presents the tagline “Your Field. Your Future. Connected.”

The landing, login, and registration pages and authenticated navigation now use these brand styles. The signed-in navigation follows the wireframe's horizontal logo / Dashboard / Apply / profile layout. The placeholder FastStarter landing copy and demo-login footer have been removed; authentication and `/config` remain available.

## Implementation notes

One named workflow at a time. Include verify notes and polish / model revisions (Phase 5). Do not treat the first build as final.

## Deployed app

Phase 6. Public Render URL (not localhost). Markers open this to mark the three workflows.

https://

## Logins

Every account a marker needs, including extra users you added. Starter accounts:

- bob / bobpass — regular user
- admin / adminpass — admin

## YouTube URL

## Session transcripts

Filled when the Guide builds the report: the agent writes each Guide chat to `docs/transcripts/<slug>.md` (Copilot Agent, Cursor, or OpenCode). `python manage.py report` packages them. Do not paste chats here during the build.

## Competency (student-judge)

Filled when the report is built. Guide runs student-judge, writes `docs/judge.md`, and export appends the scorecard here.

## Skill integrity

Filled by `python manage.py report`. Do not edit the course skills.
