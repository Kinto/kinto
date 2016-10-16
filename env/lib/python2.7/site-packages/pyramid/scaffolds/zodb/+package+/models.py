from persistent.mapping import PersistentMapping


class MyModel(PersistentMapping):
    __parent__ = __name__ = None


def appmaker(zodb_root):
    if 'app_root' not in zodb_root:
        app_root = MyModel()
        zodb_root['app_root'] = app_root
        import transaction
        transaction.commit()
    return zodb_root['app_root']
