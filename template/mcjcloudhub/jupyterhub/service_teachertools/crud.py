from typing import Any

from sqlmodel import Session, select, delete
from sqlalchemy.dialects import (sqlite, postgresql, mysql,
                                 oracle, mssql)

from models import (Student,
                    StudentCreate,
                    Cell,
                    CellCreate,
                    CellUpdate,
                    Log,
                    LogCreate,
                    LogUpdate)


def upsert(session: Session, table: Any, values: list[dict],
           index_elements: list[str]):
    """update or ignoreを実行する
    """

    dialect_map = {
        "mssql": mssql,
        "mysql": mysql,
        "oracle": oracle,
        "postgresql": postgresql,
        "sqlite": sqlite,
    }
    insert_stmt = dialect_map[session.bind.dialect.name].insert(table).values(values)
    do_nothing_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements=index_elements)
    session.exec(do_nothing_stmt)


def create_students(*, session: Session, students_create: list[StudentCreate],
                    skip_exists=True) -> list[Student]:
    """学生テーブルにデータを追加する
    """
    db_obj_list = list()
    for row in students_create:
        db_obj = Student.model_validate(
            row
        )
        db_obj_list.append(db_obj)

    if skip_exists is False:
        session.add_all(db_obj_list)

    else:
        upsert(session, Student,
               [student_create.to_dict() for student_create in students_create], ["id"])

    session.commit()
    return db_obj_list


def delete_student_all(*, session: Session) -> Any:
    session.exec(delete(Student))
    session.commit()


def create_cells(*, session: Session, cells_create: list[CellCreate],
                 skip_exists=False) -> list[Cell]:
    """セル定義テーブルにデータを追加する
    """
    db_obj_list = list()
    for row in cells_create:
        db_obj = Cell.model_validate(
            row
        )
        db_obj_list.append(db_obj)

    if skip_exists is False:
        session.add_all(db_obj_list)
    else:
        upsert(session, Cell,
               [cell_create.to_dict() for cell_create in cells_create],
               ["id", "assignment"])

    return db_obj_list


def update_cell(*, session: Session, db_cell: Cell, cell_in: CellUpdate) -> Any:
    cell_data = cell_in.model_dump(exclude_unset=True)
    extra_data = {}
    db_cell.sqlmodel_update(cell_data, update=extra_data)
    session.add(db_cell)
    return db_cell


def delete_cell(*, session: Session, db_cell: Cell) -> Any:
    session.delete(db_cell)
    return db_cell


def delete_cell_all(*, session: Session) -> Any:
    session.exec(delete(Cell))


def create_logs(*, session: Session, log_creates: list[LogCreate], skip_exists=False) -> list[Log]:

    db_obj_list = list()
    for row in log_creates:
        db_obj = Log.model_validate(
            row
        )
        db_obj_list.append(db_obj)

    if skip_exists is False:
        session.add_all(db_obj_list)
    else:
        upsert(session, Log,
               [log_create.to_dict() for log_create in log_creates],
               ["assignment", "student_id", "cell_id", "log_sequence"])

    return db_obj_list


def update_log(*, session: Session, db_log: Log, log_in: LogUpdate) -> Any:
    log_data = log_in.model_dump(exclude_unset=True)
    extra_data = {}
    db_log.sqlmodel_update(log_data, update=extra_data)
    session.add(db_log)
    return db_log


def delete_logs(*, session: Session, assignment: str = None,
                student_id: str = None, cell_id: str = None,
                notebook_name: str = None) -> Any:
    stmt = delete(Log)
    conditions = []

    if assignment is not None:
        conditions.append(Log.assignment == assignment)
    if student_id is not None:
        conditions.append(Log.student_id == student_id)
    if cell_id is not None:
        conditions.append(Log.cell_id == cell_id)
    if notebook_name is not None:
        conditions.append(Log.notebook_name == notebook_name)

    if conditions:
        stmt = stmt.where(*conditions)

    session.exec(stmt)


def delete_log_all(*, session: Session) -> Any:
    session.exec(select(Log)).delete()
