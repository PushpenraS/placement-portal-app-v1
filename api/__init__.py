from .auth_routes import LoginUser, LogoutUser, EmailAvailability
from .register_routes import RegisterCandidate, RegisterEmployer
from .admin_routes import (
    AdminEmployerResource,
    AdminCandidateResource,
    AdminPlacementDriveItemResource,
    AdminPlacementDriveListResource,
    AdminCandidateApplicationItemResource,
    AdminCandidateApplicationListResource,
)
from .employer_routes import (
    EmployerResource,
    EmployerPlacementDriveResource,
    EmployerPlacementDriveItemResource,
    EmployerDriveApplicationListResource,
    EmployerApplicationItemResource,
)
from .candidate_routes import (
    CandidateResource,
    CandidateDriveApplicationResource,
    CandidateDriveItemResource,
    CandidateAppliedDriveListResource,
    CandidateEmployerItemResource,
    CandidateEmployerListResource,
    CandidateApplicationHistoryResource,
)
