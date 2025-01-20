DISCOVER_EVENT = """
You are an agent browsing the web helping discover events where people concentrate in specific areas at given date times. 

Please help me identify such events happening as per below
near location: {location}, Germany
timeframe: {time}
type: {event_type}
description: {event_description}

 For each please give me a table including name, location details with complete address, start and end date (in format of YYYY-MM-DD), start and end times, type as event_type, 
 reference web link, and size in S, M, L, XL (for size use S if I can expect <100 people, M for people between 100 to 500, L for people upto 5000 and XL for above 5000).

"""