def includeme(config):
    config.add_api_capability(
        "history",
        description="Track changes on data.",
        url="https://kinto.readthedocs.io")
