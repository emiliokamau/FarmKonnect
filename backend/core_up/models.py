from backend.backend.models import *  # noqa: F401,F403

# Keep the app label stable for Django's app registry and custom user model.
# The class definitions are re-exported here so the app can be referenced as
# "core_up" without collapsing the duplicate backend package namespace.
