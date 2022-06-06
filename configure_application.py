from twitivity import Activity
import os

CB_URL = os.environ['callback_url']

account_activity = Activity()
print(
    account_activity.register_webhook(
        callback_url=CB_URL)
        )
print(account_activity.subscribe())
