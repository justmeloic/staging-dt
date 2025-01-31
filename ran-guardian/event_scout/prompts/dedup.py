DEDUPLICATE_EVENTS = """Your job is to check if there are any duplicate events
and then if there are, provide the event IDs of all the duplicate events.

Please don't write explicit code for deduplication but rely on your ability to identify those by looking and comparing at the data directly.
Please use only the "name", "address", "start_date", and "end_date" fields to determine if the event is a duplicate.

Finally, return json containing the duplicate events, containing the duplicate event ID, name, address, start date, end date.

Here is the json of the events:
{events}
"""