

By default we should be protecting our `/api/` endpoints with the `@token_required` decorator. Remember to add the `current_user`/`user` explicit parameter to the decorated function!

For mongoengine `Documents`, use `.id`, NOT `._id`

variable names: be specific with labels. e.g. user should represent a `User` object, `user_id` should represent a `user_id`. assume abstract nouns signify objects, and have properties associated with them like names, ids, etc., unless the contrary is clearly obvious.
