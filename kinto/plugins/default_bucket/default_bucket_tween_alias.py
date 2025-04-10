from pyramid.response import Response


def default_bucket_tween_alias(handler, registry):
    def tween(request):
        # Manually Authenticating the user
        userid = request.authenticated_userid

        if not userid:
            # Reject unauthenticated requests
            return Response(json={"message": "No userid"}) # Skip if unauthenticated3

        request.prefixed_userid = f'account:{userid}'
        # Authentication complete
        path = request.path
        if not path.endswith("buckets/default"):
            bucket_id = request.default_bucket_id
            if path.endswith(f"buckets/{bucket_id}"):
                # Convert to /buckets/default
                next_segment = path.split("/")[3]
                new_path = path.replace(f"/buckets/{next_segment}", "/buckets/default")
                request.environ["PATH_INFO"] = new_path
        return handler(request)
    return tween
