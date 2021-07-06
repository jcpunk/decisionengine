"""
    Code not written by us
"""
__all__ = [
    "orm_as_dict",
    "clone_model",
]

import sqlalchemy


def orm_as_dict(obj):
    """ Based on : https://stackoverflow.com/a/37350445 """
    return {
        c.key: getattr(obj, c.key) for c in sqlalchemy.inspect(obj).mapper.column_attrs
    }


def clone_model(model, **kwargs):
    """ Based on https://stackoverflow.com/a/55991358 """
    # will raise AttributeError if data not loaded
    try:
        model.sequence_id  # taskmanager doesn't have an 'id' column
    except AttributeError:
        model.id  # pylint: disable=pointless-statement

    table = model.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key]
    data = {c: getattr(model, c) for c in non_pk_columns}
    data.update(kwargs)

    return model.__class__(**data)
