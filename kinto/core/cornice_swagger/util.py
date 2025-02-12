import colander

from kinto.core.cornice.validators import colander_body_validator


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


def body_schema_transformer(schema, args):
    validators = args.get("validators", [])
    if colander_body_validator in validators:
        body_schema = schema
        schema = colander.MappingSchema()
        schema["body"] = body_schema
    return schema


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
