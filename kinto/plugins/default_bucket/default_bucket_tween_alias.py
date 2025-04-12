def default_bucket_tween_alias(handler, registry):
    def tween(request):
        # Manually Authenticating the user
        userid = request.authenticated_userid

        if not userid:
            # Reject unauthenticated requests
            return handler(request)

        # Authentication complete
        path = request.path
        if "buckets/default" not in path:
            original_bucket_id = request.default_bucket_id
            path_segments = path.rstrip("/").split("/")
            last_segment = path_segments[-1] if path_segments else ""

            # Determine whether dashes are allowed based on the path
            if "-" in last_segment:
                adjusted_bucket_id = original_bucket_id
            else:
                adjusted_bucket_id = original_bucket_id.replace("-", "")

            if f"buckets/{adjusted_bucket_id}" in path:
                # Convert to /buckets/default
                next_segment = path.split("/")[3]
                new_path = path.replace(f"/buckets/{next_segment}", "/buckets/default")
                request.environ["PATH_INFO"] = new_path
        return handler(request)

    return tween
