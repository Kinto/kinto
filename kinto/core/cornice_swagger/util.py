def trim(docstring):
    """
    Remove the tabs to spaces, and remove the extra spaces / tabs that are in
    front of the text in docstrings.

    Implementation taken from http://www.python.org/dev/peps/pep-0257/
    """
    if not docstring:
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    lines = [line.strip() for line in lines]
    res = "\n".join(lines)
    return res


def merge_dicts(base, changes):
    """Merge b into a recursively, without overwriting values.

    :param base: the dict that will be altered.
    :param changes: changes to update base.
    """
    for k, v in changes.items():
        if isinstance(v, dict):
            merge_dicts(base.setdefault(k, {}), v)
        else:
            base.setdefault(k, v)
