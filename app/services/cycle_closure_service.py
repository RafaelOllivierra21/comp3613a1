from app.models.application import Application, InternshipCycle
from app.models.position import Position
from app.models.user import User
from app.repositories.cycle_closure import CycleClosureRepository
from app.services.application_service import CycleClosedError
from app.services.matching_service import NotCoordinatorError


class CycleClosureService:
    def __init__(self, repository: CycleClosureRepository):
        self.repository = repository

    def close_cycle(self, user: User) -> int:
        self._require_coordinator(user)
        cycle = self.repository.get_current_cycle()
        if (
            cycle is None
            or cycle.cycleID is None
            or cycle.status.strip().casefold() != "open"
        ):
            raise CycleClosedError

        applications = self.repository.get_applications_for_cycle(cycle.cycleID)
        active_match_counts = self.repository.get_active_match_counts(cycle.cycleID)
        applications_to_update: list[Application] = []
        for application in applications:
            normalized_status = application.status.strip().casefold().replace("_", " ")
            if (
                normalized_status in {"submitted", "awaiting rematch"}
                and active_match_counts.get(application.applicationID, 0) == 0
            ):
                application.status = "not matched"
                applications_to_update.append(application)

        positions = self.repository.get_open_positions_for_cycle(cycle.cycleID)
        for position in positions:
            position.status = "closed"
        cycle.status = "closed"
        self.repository.save_closure(cycle, positions, applications_to_update)
        return len(applications_to_update)

    @staticmethod
    def _require_coordinator(user: User) -> None:
        if user.role.strip().casefold() != "coordinator":
            raise NotCoordinatorError
