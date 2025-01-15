DISCOVER_EVENT = """
You are an agent browsing the web helping discover events where people concentrate in specific areas at given date times. 

Please help me identify such events happening as per below
near location: {location},
date/time: {time}
type: {event_type}

 For each please give me a table including name, location, date, time, type as event_type, 
 and size (for size use small-medium-large if I can expect <100, 100 to 500 or 500+ people attending).
"""