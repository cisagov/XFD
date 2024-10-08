# Third-Party Libraries
from fastapi import HTTPException


def sort_direction(sort, order):
    """
    Adds the sort direction modifier.
    If sort =
        ASC - return order field unmodified to sort in ascending order.
        DSC - returns & prepend '-' to the order field to sort in descending order.
    """
    try:
        # Fetch all domains in list
        if sort == "ASC":
            return order
        elif sort == "DSC":
            return "-" + order
        else:
            raise ValueError
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Invalid sort direction supplied")
