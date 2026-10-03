from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError
from app.models.application import Application
from app.models.application import InternshipCycle, Skill, Student
from app.models.user import User
from app.repositories.application import ApplicationRepository


class ApplicationError(Exception):
    pass


class AlreadyAppliedError(ApplicationError):
    pass


class CycleClosedError(ApplicationError):
    pass


class StudentIDTakenError(ApplicationError):
    pass


class InvalidStudentIDInputError(ApplicationError):
    pass


class InvalidGPAInputError(ApplicationError):
    pass


class InvalidDegreeNameInputError(ApplicationError):
    pass


class InvalidExpectedGraduationDateInputError(ApplicationError):
    pass


class InvalidResumeLinkInputError(ApplicationError):
    pass


class InvalidSkillIDsInputError(ApplicationError):
    pass


class NotAStudentError(ApplicationError):
    pass


@dataclass(frozen=True)
class ApplicationPageState:
    cycle: InternshipCycle | None
    student: Student | None
    application: Application | None
    available_skills: list[Skill]
    selected_skills: list[Skill]

    @property
    def cycle_is_open(self) -> bool:
        return self.cycle is not None and self.cycle.status.casefold() == "open"


class ApplicationService:
    def __init__(self, application_repository: ApplicationRepository):
        self.application_repository = application_repository

    def submit_application(
        self,
        user: User,
        student_id: int,
        gpa: float,
        degree_name: str,
        expected_graduation_date: date,
        resume_link: str,
        skill_ids: list[int],
    ) -> Application:
        self._require_student(user)
        if user.id is None:
            raise NotAStudentError

        cycle = self.application_repository.get_current_cycle()
        if cycle is None or cycle.status.casefold() != "open":
            raise CycleClosedError
        if student_id <= 0:
            raise InvalidStudentIDInputError

        if self.application_repository.get_application_for_user_cycle(user.id, cycle.cycleID):
            raise AlreadyAppliedError
        if self.application_repository.get_student_by_id(student_id):
            raise StudentIDTakenError
        if not 0 <= gpa <= 4.3:
            raise InvalidGPAInputError
        if not degree_name.strip():
            raise InvalidDegreeNameInputError
        if expected_graduation_date < date.today():
            raise InvalidExpectedGraduationDateInputError

        parsed_resume_url = urlparse(resume_link.strip())
        if parsed_resume_url.scheme not in {"http", "https"} or not parsed_resume_url.netloc:
            raise InvalidResumeLinkInputError
        if not skill_ids or len(set(skill_ids)) != len(skill_ids):
            raise InvalidSkillIDsInputError
        if len(self.application_repository.get_skills_by_ids(skill_ids)) != len(skill_ids):
            raise InvalidSkillIDsInputError

        student = Student(
            studentID=student_id,
            userID=user.id,
            gpa=gpa,
            degreeName=degree_name.strip(),
            expectedGraduationDate=expected_graduation_date,
            resumeLink=resume_link.strip(),
        )
        application = Application(
            studentID=student_id,
            cycleID=cycle.cycleID,
            dateSubmitted=date.today(),
        )
        try:
            return self.application_repository.create_submission(
                student,
                application,
                skill_ids,
            )
        except IntegrityError as exc:
            if self.application_repository.get_application_for_user_cycle(user.id, cycle.cycleID):
                raise AlreadyAppliedError from exc
            if self.application_repository.get_student_by_id(student_id):
                raise StudentIDTakenError from exc
            raise

    def get_dashboard_state(self, user: User) -> ApplicationPageState:
        return self._get_state(user)

    def get_application_page_state(self, user: User) -> ApplicationPageState:
        state = self._get_state(user)
        if state.application is None and not state.cycle_is_open:
            raise CycleClosedError
        return state

    def _get_state(self, user: User) -> ApplicationPageState:
        self._require_student(user)
        cycle = self.application_repository.get_current_cycle()
        student = (
            self.application_repository.get_student_by_user_id(user.id)
            if user.id is not None
            else None
        )
        application = None
        selected_skills: list[Skill] = []
        if cycle is not None and student is not None:
            application = self.application_repository.get_application_for_student_cycle(
                student.studentID,
                cycle.cycleID,
            )
            if application is not None:
                selected_skills = self.application_repository.get_skills_for_student(
                    student.studentID,
                )

        return ApplicationPageState(
            cycle=cycle,
            student=student,
            application=application,
            available_skills=self.application_repository.get_all_skills(),
            selected_skills=selected_skills,
        )

    @staticmethod
    def _require_student(user: User) -> None:
        if user.role.casefold() != "student":
            raise NotAStudentError
