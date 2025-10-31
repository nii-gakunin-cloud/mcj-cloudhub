from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, Relationship, SQLModel, create_engine, Session
from sqlalchemy import Column, JSON
from sqlalchemy.schema import UniqueConstraint
from typing import Dict


def default_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z')


class CellBase(SQLModel):
    id: str = Field(max_length=255, primary_key=True)
    assignment: str = Field(max_length=255)
    section: str = Field(max_length=255)
    notebook_name: str | None = Field(default=None, max_length=255)
    jupyter_cell_id: str | None = Field(default=None, max_length=255)
    nbgrader_cell_id: str | None = Field(default=None, max_length=255)


class CellCreate(CellBase):

    def to_dict(self):
        return dict(
            id=self.id,
            assignment=self.assignment,
            section=self.section,
            notebook_name=self.notebook_name,
            jupyter_cell_id=self.jupyter_cell_id,
            nbgrader_cell_id=self.nbgrader_cell_id
        )


class CellUpdate(CellBase):
    pass


class Cell(CellBase, table=True):
    logs: list["Log"] = Relationship(back_populates="cell",
                                     cascade_delete=True)
    __table_args__ = (
        UniqueConstraint("id", "assignment"),
    )


class StudentBase(SQLModel):
    id: str = Field(max_length=255, primary_key=True)


class StudentCreate(StudentBase):

    def to_dict(self):
        return dict(
            id=self.id,
        )


class StudentUpdate(StudentBase):
    pass


class Student(StudentBase, table=True):
    logs: list["Log"] = Relationship(back_populates="student",
                                     cascade_delete=True)


class LogBase(SQLModel):
    assignment: str = Field(max_length=255)
    student_id: str | None = Field(default=None, foreign_key="student.id")
    cell_id: str | None = Field(default=None, foreign_key="cell.id")
    log_sequence: int = Field(default=0)
    notebook_name: str | None = Field(default=None, max_length=255)
    log_json: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    log_code: str | None = Field(default=None, max_length=255)
    log_path: str | None = Field(default=None, max_length=255)
    log_start: datetime | None = Field(default=None)
    log_end: datetime | None = Field(default=None)
    log_size: float | None = Field(default=None)
    log_server_signature: str | None = Field(default=None, max_length=255)
    log_uid: int
    log_gid: int
    log_notebook_path: str | None = Field(default=None, max_length=255)
    log_lc_notebook_meme: str | None = Field(default=None, max_length=255)
    log_execute_reply_status: str | None = Field(default=None, max_length=255)


class LogCreate(LogBase):
    def to_dict(self):
        return dict(
            assignment=self.assignment,
            student_id=self.student_id,
            cell_id=self.cell_id,
            log_sequence=self.log_sequence,
            notebook_name=self.notebook_name,
            log_json=self.log_json,
            log_code=self.log_code,
            log_path=self.log_path,
            log_start=self.log_start,
            log_end=self.log_end,
            log_size=self.log_size,
            log_server_signature=self.log_server_signature,
            log_uid=self.log_uid,
            log_gid=self.log_gid,
            log_notebook_path=self.log_notebook_path,
            log_lc_notebook_meme=self.log_lc_notebook_meme,
            log_execute_reply_status=self.log_execute_reply_status
        )


class LogUpdate(LogBase):
    pass


class Log(LogBase, table=True):
    id: int | None = Field(default=None, primary_key=True)  # Noneの場合自動発番される
    student: Student | None = Relationship(back_populates="logs")
    cell: Cell | None = Relationship(back_populates="logs")

    __table_args__ = (
        UniqueConstraint("assignment", "student_id", "cell_id", "log_sequence"),
    )


class LineItem(BaseModel):
    model_config = ConfigDict(strict=True)

    label: str
    scoreMaximum: float
    resourceId: str | None = ""
    tag: str | None = "grade"
    startDateTime: str | None = "2025-04-01T16:05:02Z"
    endDateTime: str | None = "2100-01-01T00:00:00Z"


class Score(BaseModel):
    model_config = ConfigDict(strict=True)

    userId: int
    scoreGiven: float
    scoreMaximum: float
    comment: str | None = ""
    timestamp: str | None = Field(default_factory=default_timestamp)
    activityProgress: str | None = "Submitted"
    gradingProgress: str | None = "FullyGraded"


def init_db(url):
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)


def test():
    engine = create_engine('sqlite:///testdb.sqlite')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        print(f'engine is {session.bind.dialect.name}')


if __name__ == '__main__':
    test()
