import kinto_http

try:
    # Initialize Kinto client
    client = kinto_http.Client(server_url="http://127.0.0.1:8888/v1", auth=("postgres", "postgres"))

    # Define the bucket, collection, and record
    bucket_name = "blog"
    collection_name = "posts"
    record_data = {"title": "Testing Initial Run", "content": "This is the content of my testing post."}

    # Ensure the bucket exists (try fetching it first)
    try:
        client.get_bucket(id=bucket_name)
    except kinto_http.KintoException:
        client.create_bucket(id=bucket_name)

    # Ensure the collection exists
    try:
        client.get_collection(collection_name, bucket=bucket_name)
    except kinto_http.KintoException:
        client.create_collection(id=collection_name, bucket=bucket_name)

    # Add a new post to the collection
    new_post = client.create_record(data=record_data, bucket=bucket_name, collection=collection_name)

    print("New post created:", new_post)

except kinto_http.KintoException as e:
    print("Error creating post:", e)
