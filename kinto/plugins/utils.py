def parse_resource(resource):
            parts = resource.split('/')
            if len(parts) == 2:
                bucket, collection = parts
            elif len(parts) == 5:
                _, _, bucket, _, collection = parts
            else:
                raise ValueError(error_msg)
            return {
                'bucket': bucket,
                'collection': collection
            }
