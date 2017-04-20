
try:
    from colander import MappingSchema, SchemaNode, String
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    class AccountSchema(MappingSchema):
        nickname = SchemaNode(String(), location='body', type='str')
        city = SchemaNode(String(), location='body', type='str')
