1. Assume the root for pytest is `backend`.
2. For integration tests, operate inside the original Docker container
3. unit and integration each have their own conftest
4. Relevant files for testing: .env, .env.test, pytest.ini, each conftest.py
