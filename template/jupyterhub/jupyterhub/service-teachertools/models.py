from datetime import datetime, timezone
from typing import Union, Optional

from pydantic import BaseModel, ConfigDict, Field


def default_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z')


class LineItem(BaseModel):
    model_config = ConfigDict(strict=True)

    label: str
    scoreMaximum: Union[int, float]
    resourceId: Optional[str] = ""
    tag: Optional[str] = "grade"
    startDateTime: Optional[str] = "2025-04-01T16:05:02Z"
    endDateTime: Optional[str] = "2100-01-01T00:00:00Z"


class Score(BaseModel):
    model_config = ConfigDict(strict=True)

    userId: int
    scoreGiven: Union[int, float]
    scoreMaximum: Union[int, float]
    comment: Optional[str] = ""
    timestamp: Optional[str] = Field(default_factory=default_timestamp)
    activityProgress: Optional[str] = "Submitted"
    gradingProgress: Optional[str] = "FullyGraded"

