class TutorialLoadTestMixin(object):
    def play_full_tutorial(self):
        self.play_user_default_bucket_tutorial()
        self.play_user_shared_bucket_tutorial()

    def play_user_default_bucket_tutorial(self):
        # Create a new task - 201 created with data.status and
        # permission.write

        # Create a new one with PUT and If-None-Match: "*"

        # Fetch the collection list and see the tasks (save the etag)

        # Fetch the collection from the Etag and see nothing new

        # Update a task

        # Try an update with If-Match on the saved ETag and see it fails

        # Get the list of records and update the ETag

        # Try an update with If-Match on the new ETag and see it works

        # Delete the record with If-Match

        # Try the collection get with the ``_since`` parameter
        pass

    def play_user_shared_bucket_tutorial(self):
        # Create a new bucket and check for permissions

        # Create a new collection and check for permissions

        # Create a new tasks for Alice

        # Create a new tasks for Bob

        # Share Alice's task with Bob

        # Check that Bob can access it

        # Create Alice's friend group with Bob and Mary

        # Give Alice's task permission for that group

        # Try to access Alice's task with Mary

        # Check that Mary's collection_get sees Alice's task

        # Check that Bob's collection_get sees both his and Alice's tasks
        pass
