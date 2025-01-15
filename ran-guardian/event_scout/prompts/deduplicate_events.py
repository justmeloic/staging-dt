DEDUPLICATE_EVENTS = prompt = """Given the tools available your job is to read the data from the database, 
check if there are any duplicate events
and then if there are, make sure you keep only one making use of the update and delete functions. 
The duplicated events won't be exactly identical so you will need to look for similarly looking events as well. 
Please don't write explicit code for deduplication but rely on your ability to identify those by looking and comparing at the data directly.

Finally, return the full list of actions you did.
in all function calls use data_type={table_name} as this is the table I want to deduplicate
"""
