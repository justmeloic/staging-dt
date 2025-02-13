VERIFY_EVENT = """Your job is to verify and check for factual correctness of a people gathering event,
scheduled in the year 2025, provided to you in json format.

Please verify the event name, start date and time, end date and time, size of the event and other details provided in the event json.

# Instructions #
Use the tool provided to get contents of the event url and double check the details.
Search for events in the year 2025 only.

Finally, provide a confidence score for the event on a scale of 1 to 10 (1 being the lowest and 10 being the highest)
based on the following criteria. Aslo provides the correct or updated details of the event if applicable.

# Confidence Score criteria #
Event details provided in the json match with the contents of the event URL.

Provide your justification in detail.
Here is the json of the events:
{event_details}
"""