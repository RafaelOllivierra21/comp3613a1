from datetime import date, timedelta
import unittest

import pytest
from sqlmodel import select

from app.models.application import Application, Student, StudentSkill
from app.repositories.application import ApplicationRepository
from app.repositories.user import UserRepository
from app.services.application_service import (
    AlreadyAppliedError,
    ApplicationService,
    StudentIDTakenError,
)
from app.services.auth_service import AuthService


class ApplicationIntegrationTests(unittest.TestCase):
    def _register_student(self, username):
        return AuthService(UserRepository(self.session)).register_user(
            username=username,
            email=f"{username}@example.com",
            password="secure-password",
            full_name=username.replace("-", " ").title(),
            number="868-555-0105",
        )

    def _submit_application(self, user, student_id):
        return ApplicationService(ApplicationRepository(self.session)).submit_application(
            user=user,
            student_id=student_id,
            gpa=3.6,
            degree_name="Computer Science",
            expected_graduation_date=date.today() + timedelta(days=365),
            resume_link="https://example.com/resume",
            skill_ids=[1, 2],
        )

    def test_submit_application(self):
        user = self._register_student("applicant-one")
        application = self._submit_application(user, student_id=1001)

        self.session.expire_all()
        saved_student = self.session.get(Student, 1001)
        application_repository = ApplicationRepository(self.session)
        saved_application = application_repository.get_application_for_user_cycle(
            user.id,
            1,
        )
        selected_skills = application_repository.get_skills_for_student(1001)
        saved_skills = self.session.exec(
            select(StudentSkill).where(StudentSkill.studentID == 1001)
        ).all()

        self.assertIsNotNone(saved_student)
        self.assertEqual(saved_student.userID, user.id)
        self.assertIsNotNone(saved_application)
        self.assertEqual(saved_application.studentID, 1001)
        self.assertEqual(saved_application.cycleID, 1)
        self.assertEqual(saved_application.status, "submitted")
        self.assertEqual(saved_application.dateSubmitted, date.today())
        self.assertEqual(
            {student_skill.skillID for student_skill in saved_skills},
            {1, 2},
        )
        self.assertEqual({skill.skillID for skill in selected_skills}, {1, 2})

    def test_apply_twice(self):
        user = self._register_student("applicant-two")
        first_application = self._submit_application(user, student_id=1002)

        with pytest.raises(AlreadyAppliedError):
            self._submit_application(user, student_id=1002)

        self.session.expire_all()
        applications = self.session.exec(
            select(Application).where(Application.studentID == 1002)
        ).all()

        self.assertEqual(len(applications), 1)
        self.assertEqual(applications[0].applicationID, first_application.applicationID)

    def test_duplicate_student_id(self):
        first_user = self._register_student("applicant-three")
        second_user = self._register_student("applicant-four")
        self._submit_application(first_user, student_id=1003)

        with pytest.raises(StudentIDTakenError):
            self._submit_application(second_user, student_id=1003)

        self.session.expire_all()
        students = self.session.exec(
            select(Student).where(Student.studentID == 1003)
        ).all()
        applications = self.session.exec(
            select(Application).where(Application.studentID == 1003)
        ).all()

        self.assertEqual(len(students), 1)
        self.assertEqual(students[0].userID, first_user.id)
        self.assertEqual(len(applications), 1)
