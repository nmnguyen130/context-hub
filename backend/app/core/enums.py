from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class PlanTier(StrEnum):
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class InvitationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class DLPAction(StrEnum):
    MASK = "MASK"
    REJECT = "REJECT"
    NONE = "NONE"
