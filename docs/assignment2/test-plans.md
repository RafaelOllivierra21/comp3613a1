# InternBridge Unit and Integration Test Plans

Source of truth for the pytest suites. Test names must match exactly.

## Unit Test Plan

Unit tests check each module in isolation. Services are tested with mocked repositories, so no test reads or writes the database.

| Unit Test | Input | Expected Output |
| --- | --- | --- |
| test_new_user() | User(username="bob", email="bob@mail.com", fullName="Bob Smith", number="868-555-0101", password="bobpass", role="student") | user.username == "bob"<br>user.role == "student" |
| test_new_position() | Position(companyID=1, cycleID=1, title="IT Intern", description="Support desk", status="open") | position.title == "IT Intern"<br>position.status == "open" |
| test_hashed_password() | encrypt_password("mypass") | result != "mypass" |
| test_check_password() | verify_password("mypass", encrypt_password("mypass")) | True |
| test_check_wrong_password() | verify_password("wrong", encrypt_password("mypass")) | False |
| test_create_token() | create_access_token({"sub": "1", "role": "student"}) | decoded token sub == "1"<br>decoded token role == "student"<br>decoded token has an exp time |
| test_authenticate_bad_password() | AuthService.authenticate_user("bob", "wrong")<br>mocked repository returns bob | None |
| test_status_label() | status_label("awaiting_rematch") | "Awaiting Rematch" |
| test_status_badge_class() | status_badge_class("rejected by company") | "status-badge status-negative" |
| test_apply_not_student() | ApplicationService.submit_application(...)<br>user with role company_rep | raises NotAStudentError |
| test_apply_cycle_closed() | ApplicationService.submit_application(...)<br>mocked cycle status "closed" | raises CycleClosedError |
| test_apply_invalid_gpa() | ApplicationService.submit_application(..., gpa=5.0)<br>mocked open cycle | raises InvalidGPAInputError |
| test_fit_percentage() | MatchingService.get_matching_page_state(...)<br>position requires skills 1, 2, 3<br>student has skills 1, 2 | fit_percentage == 66.67 |
| test_suggestions_top_three() | MatchingService.get_matching_page_state(...)<br>5 positions at 100%, 67%, 50%, 33%, 0% | 3 suggestions<br>order 100%, 67%, 50% |
| test_suggestion_tiebreak() | MatchingService.get_matching_page_state(...)<br>"Law Intern" and "IT Intern" both at 50% | "IT Intern" listed first |
| test_offer_before_interview() | CandidateSelectionService.process_company_action(action="offer")<br>mocked match status matched | raises InvalidActionError |
| test_offer_already_pending() | CandidateSelectionService.process_company_action(action="offer")<br>another candidate is offered | raises OfferAlreadyPendingError |
| test_post_position_blank_title() | PositionPostingService.create_position(..., title="   ") | raises InvalidTitleInputError |
| test_close_cycle_not_coordinator() | CycleClosureService.close_cycle(...)<br>user with role student | raises NotCoordinatorError |

## Integration Testing Plan

Integration tests run against an isolated SQLite test database, created fresh for each test and seeded with the open internship cycle and the skill list.

| Test | Dependencies | Description |
| --- | --- | --- |
| test_register_user() | AuthService.register_user()<br>UserRepository.get_by_username() | Ensures the user record is saved with role student and a hashed password |
| test_authenticate() | AuthService.register_user()<br>AuthService.authenticate_user() | Ensures authenticate_user() returns a token when given the correct credentials |
| test_get_all_users() | UserRepository.create()<br>UserService.get_all_users() | Verifies every created user is returned |
| test_submit_application() | AuthService.register_user()<br>ApplicationService.submit_application()<br>get_application_for_user_cycle()<br>get_skills_for_student() | Ensures the Student, Application and StudentSkill records are created with the correct IDs, status submitted and today's date |
| test_apply_twice() | ApplicationService.submit_application() | Ensures a second application in the same cycle raises AlreadyAppliedError and only one application record exists |
| test_duplicate_student_id() | AuthService.register_user()<br>ApplicationService.submit_application() | Ensures a second student using the same UWI ID raises StudentIDTakenError |
| test_create_position() | PositionPostingService.create_position()<br>MatchingRepository.get_required_skills() | Ensures the position is saved with the rep's companyID, the cycleID, status open, today's date and its PositionSkill records |
| test_submit_match() | submit_application()<br>create_position()<br>MatchingService.submit_match()<br>get_current_matches() | Ensures a Match record is created with status matched and the application's status becomes matched |
| test_match_pair_twice() | MatchingService.submit_match() | Ensures matching the same application and position twice raises PairAlreadyMatchedError |
| test_interview_and_offer() | submit_match()<br>CandidateSelectionService.process_company_action()<br>get_match() | Ensures the match moves to interviewing, then offered |
| test_reject_last_match() | submit_match()<br>process_company_action()<br>get_application() | Ensures the match becomes rejected by company and an application with no other active match becomes awaiting rematch |
| test_accept_offer() | submit_match()<br>process_company_action()<br>CandidateSelectionService.process_student_action() | Ensures the match becomes accepted, the position becomes filled, the application becomes placed, the student's other matches close as placed elsewhere and other candidates' matches close as position filled |
| test_decline_offer() | process_company_action()<br>process_student_action() | Ensures the match becomes declined by student and the position can then be offered to another interviewing candidate |
| test_close_cycle() | CycleClosureService.close_cycle()<br>get_applications_for_cycle()<br>get_open_positions_for_cycle() | Ensures the cycle and its open positions become closed, submitted and awaiting rematch applications become not matched, matched applications stay matched, and the returned count is correct |
| test_closed_cycle_blocks_new_work() | close_cycle()<br>submit_match()<br>create_position()<br>process_company_action() | Ensures new matches and positions raise CycleClosedError, while actions on existing matches still work |
