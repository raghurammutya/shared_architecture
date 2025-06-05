from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, TIMESTAMP
from typing import Dict

Base = declarative_base()

def generate_dynamic_model(table_name: str, fields: Dict[str, str]):
    """
    Dynamically generates a SQLAlchemy model for the given table_name and fields.
    Supported field types: 'int', 'str', 'timestamp'

    Example:
    fields = {
        "symbol": "str",
        "price": "int",
        "timestamp": "timestamp"
    }
    """
    columns = {
        "__tablename__": table_name,
        "id": Column(Integer, primary_key=True)
    }

    type_map = {
        "int": Integer,
        "str": String,
        "timestamp": TIMESTAMP
    }

    for field_name, field_type in fields.items():
        if field_type not in type_map:
            raise ValueError(f"Unsupported field type: {field_type} for field: {field_name}")
        columns[field_name] = Column(type_map[field_type])

    return type(table_name.capitalize(), (Base,), columns)
