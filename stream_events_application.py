import json

from pprint import pprint
from twitivity import Event
import os

CB_URL = os.environ['callback_url']

class StreamEvent(Event):
    CALLBACK_URL: str = CB_URL
    
    def on_data(self, data: json) -> None:
        pprint(data, indent=2)


if __name__ == "__main__":
    stream_events = StreamEvent()   
    stream_events.listen()
