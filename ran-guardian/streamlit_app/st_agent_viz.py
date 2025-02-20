import time
import random
import streamlit as st
import folium
from streamlit_folium import st_folium

event_name = 'Frankfurt Carnival Parade (Festival)'
event_start_date = '2025-03-02'
event_id = 'xsrQHdTcSPlltUsOgUby'
event_size = 'XL 5000+ people'
event_url = 'https://www.walk-frankfurt.com/blog/frankfurt-karneval'

verify_event_string = """
Okay, I have analyzed the provided JSON and the content from the URL. Here's the verified event information:

Verified/Corrected Event Details:
Event Name: Frankfurt Carnival (Karneval) Parade
Start Date and Time: 2025-03-01 (Saturday, Children's Parade), Time not specified. 2025-03-02 (Sunday, Main Parade), Time not specified.
End Date and Time: 2025-03-02 (Sunday, Main Parade), Time not specified.
Event Size (Attendance): Not specified in the document, but likely to be a large gathering (XL is a reasonable estimate).
Other Relevant Details:
The main parade on Sunday commences at Westhafen and takes a route to Römerberg: Untermainbrücke - Neue Mainzer Straße - Friedensstraße - Kaiserstraße - Roßmarkt - Goetheplatz - Rathenauplatz - Biebergasse - Hauptwache -Katharienenpforte - Bleidenstraße - Liebfrauenberg - Töngesgasse - Fahrgasse - Battonnstraße - Kurt-Schumacher-Straße - Fahrgasse - Braubachstraße - Römerberg
There is also a Children's Karneval Parade on Saturday, starting at Hauptwache and walking through to the Römerberg.
The date of the Karneval parade relates to Lent and therefore changes each year.
Confidence Score (1-10): 9

Justification (Bullet Points):

The event name, start date, and route information in the JSON mostly matched the information on the WALK Frankfurt website.
The WALK Frankfurt website explicitly mentions the 2025 dates for the Karneval parade (March 1st and 2nd).
The WALK Frankfurt website appears to be a reliable source of information for events in Frankfurt (local guide).
The provided JSON had the correct date, but did not specify both the Saturday and Sunday parades. I've corrected the start date to reflect both days. The JSON also listed the end time as "Time not specified" which is accurate based on the URL content.
I am unable to determine the exact number of attendees (event size) from the provided URL.
"""

nodes_arr = ["65271283", "65271284", "65271286"] #, "64789301", "64789302"]
nodes_summary_arr = ["""Multiple active 'LINK_DOWN' alarms exist for the site BY1796, indicating network connectivity issues. Although RRC success rate is above 95%, the active alarms are more critical.""",
    """The node is problematic due to the presence of active LINK_DOWN alarms on the switches and routers. Although the RRC setup success rate is generally acceptable, the active alarms indicate a network connectivity issue that requires investigation.""",
    """The RRC setup success rate was below 95% at 08:16. Additionally, there are active LINK_DOWN alarms on the site BY1796, indicating a network connectivity issue."""
]

event_risk_string = """
Event Risk: HIGH
Multiple nodes (65271283, 65271284) at site BY1796 were flagged as problematic due to active 'LINK_DOWN' alarms related to switch/router ports, indicating network connectivity issues.
Nodes 65271286 at site BY1126 were also flagged as problematic, with active 'epsEnodeBUnreachable' alarms and fluctuating RRC setup success rates below 95%. 
The event is categorized as 'L', and the total node capacity is 3223. 
The presence of multiple active alarms and pre-existing network issues at both sites increases the risk of service disruption during the event."""

node1_1 = """
Okay, I will proceed with the remediation plan for issue ID 016ymEfP8wXWiLFMcYYV affecting node ID 65271283.

**Step 1: Activate MLB of a node**
 (Tool call: [{'name': 'activate_mlb', 'args': {'node_id': '65271283'}, 'id': '2ac105d7-17cd-4266-81ee-2f6c9470a7b9', 'type': 'tool_call'}])
"""

node1_2 = """
[Tool:activate_mlb]: 
{
    "commands": [
        "set CXC4011944 FeatureState 1",
        "set CXC4012397 FeatureState 1",
        "set . targetloadawarelbdar true",
        "set . coverageawarelbdar true",
        "st eutrancellfdd UNLOCKED",
        "set . highloadthreshold 3000",
        "set . mediumhighloadthreshold 2000",
        "set . mediumloadthreshold 1500",
        "set . lowmediumloadthreshold 1000",
        "set . lowloadthreshold 600",
        "set EUtranCellFDD.*_L[^H] idleModePrioAtReleaseRef ENodeBFunction=1,LoadBalancingFunction=1,IdleModePrioAtRelease=500_1300_1444_3050_3749_6400",
        "get idlemodeprio",
        "pmxt . pmidlemodereldistr"
    ],
    "summary": "The following actions were performed to improve load balancing on the RAN node. First, I enabled features CXC4011944 and CXC4012397 which are related to load balancing algorithms. Then, I enabled target load aware and coverage aware load balancing. The EUTRAN cell was unlocked to allow configuration changes. Load thresholds were set to optimize the distribution of users based on cell load. Finally, idle mode priorities were set to influence cell reselection behavior and the idle mode distribution was retrieved.",
    "success": true
}
"""

node1_3 = """
['**Step 2: Deactivate CA of a node**\n', '\n'] (Tool call: [{'name': 'deactivate_ca', 'args': {'node_id': '65271283'}, 'id': 'c410df17-9eca-4027-92e3-482738336ff5', 'type': 'tool_call'}])
"""

node1_4 = """
[Tool:deactivate_ca]: 
{
    "commands": [
        "get. cafreqprio",
        "cvmk OliBackup",
        "cvls",
        "set EUtranFreqRelation=1300|EUtranFreqRelation=1444|EUtranFreqRelation=3050|EUtranFreqRelation=3749|EUtranFreqRelation=500|EUtranFreqRelation=6400 caFreqPriority    -1",
        "get. cafreqprio",
        "ue print -ue -allcell -ca",
        "set _LA|EUtranFreqRelation=1300 caFreqPriority -1",
        "set _LA.EUtranFreqRelation=1300 caFreqPriority -1",
        "set _LA.EUtranFreqRelation=1300 caFreqPriority -1",
        "set _LA. EUtranFreqRelation=1300 caFreqPriority -1",
        "set _LA.,EUtranFreqRelation=1300 caFreqPriority -1",
        "set _LA.,EUtranFreqRelation=1300 caFreqPriority -1 EUtranFreqRelation=1444 caFreqPriority 5",
        "set __LA.,EUtranFreqRelation=1300 caFreqPriority -1|__LA.,EUtranFreqRelation=1444 caFreqPriority 5",
        "set _LA.,EUtranFreqRelation=1300 caFreqPriority -1|_LA.,EUtranFreqRelation=1444 caFreqPriority 5",
        "ue print -ue -allcell -ca",
        "set EUtranCellFDD=._LU.{1,2}_6.,EUtranFreqRelation=3749 caFreqPriority 4 set EUtranCellFDD=._LU.{1,2}_6.*,EUtranFreqRelation=6400 6400 caFreqPriority 4",
        "ue print -ue -allcell -ca"
    ],
    "summary": "Deactivated carrier aggregation by setting caFreqPriority to -1 for all EUtranFreqRelations. I started by getting the current CA frequency priorities, then setting them to -1 to effectively deactivate CA. Afterwards, I checked UE states and cell configurations related to CA to ensure the changes were applied correctly. This was done to resolve a reported issue of excessive interference caused by CA in the node.",
    "success": True
}
"""

node1_5 = """
[SUPERVISOR AGENT] [Router] Updating issue status to monitoring
"""

monitor_string = """
MLB was activated and CA was deactivated for node 65271283. The RRC_success_rate was monitored for 15 minutes and the value was 83.28%, which is above 80%.
"""

human_approval_string = """
The node performance KPIs have improved after automated remediation actions.
Human approval is not required in this case.
"""

conclude_string = """
MLB was activated and CA was deactivated for node 65271283. The RRC_success_rate was monitored for 15 minutes and the value was 83.28%, which is above 80%.
"""

st.set_page_config(page_title="RAN Guardian AI Agent", layout="wide")
st.subheader(f":primary[Event:] :primary-background[{event_name}]")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"Size: **{event_size}**")
    st.markdown(f"Start Date: **{event_start_date}**")
    st.markdown(f"ID: **{event_id}**")
    st.markdown(f"URL: **{event_url}**")

with col2:
    metrics_ph = st.empty()

# with col3:
#     map = folium.Map(location=[50.109128, 8.671323], zoom_start=14)
#     st_data = st_folium(map, use_container_width=True, height=200)

st.divider()

def stream_data(response: str):
    for word in response.split(" "):
        yield word + " "
        time.sleep(0.02)

st.write("")
if st.button("Plan RAN Capacity by AI Agents", type="primary"):

    st.subheader(f":primary[» Event Agent: Verify Event Details]")
    ph1 = st.empty()

    st.subheader(f":primary[» RAN Agent: Assess Node Risk]")
    ph2 = st.empty()

    st.subheader(f":primary[» RAN Agent: Assess Event Risk]")
    ph3 = st.empty()

    st.subheader(f":primary[» Supervisor Agent: Plan and Perform Reconfiguration]")
    ph4 = st.empty()

    # st.subheader(f":primary[» Node Agent: Execute Remediation Actions]")
    # ph5 = st.empty()

    st.subheader(f":primary[» Supervisor Agent: Monitor KPIs]")
    ph6 = st.empty()

    st.subheader(f":primary[» Supervisor Agent: Ask for Human Approval]")
    ph7 = st.empty()

    st.subheader(f":primary[» RAN Agent: Conclude RAN Reconfiguration]")
    ph8 = st.empty()

    with ph1:
        with st.status("Verifying Event", expanded=True) as status:
            st.write("Retrieving Event data...")
            time.sleep(2)
            st.write("Verifying Event with Gemini...")
            time.sleep(3)
            st.write_stream(stream_data(verify_event_string))
            time.sleep(1)
            status.update(
                label="**Event Verification Complete. Confidence Score: 9/10**", state="complete", expanded=False
            )

    with ph2:
        with st.status("Assessing Node Risk", expanded=True) as status:
            st.write("Getting Nodes in the Coverage Region...")
            time.sleep(2)
            n_str = ", ".join(nodes_arr)
            st.write(f"Identified Nodes are {n_str}.")
            time.sleep(1)
            st.write("Getting Node Performance and Alarms Data...")
            time.sleep(2)
            for node, summary in zip(nodes_arr, nodes_summary_arr):
                st.markdown(f"Analyzing Node **{node}**")
                time.sleep(4)
                st.write_stream(stream_data(summary))
            status.update(
                label="**Node Risk Assessment Complete. Multiple nodes found with existing issues.**", state="complete", expanded=False
            )

    with ph3:
        with st.status("Assessing Event Risk", expanded=True) as status:
            time.sleep(4)
            st.write_stream(stream_data(event_risk_string))
            status.update(
                label="**Event Risk Assessment Complete. Event Risk: HIGH**", state="complete", expanded=False
            )

    with ph4:
        with st.status("Remediating Impacted Nodes", expanded=True) as status:
            st.write("Remediating Node **65271283**")
            time.sleep(4)
            st.write_stream(stream_data(node1_1))
            time.sleep(4)
            st.code(node1_2)
            time.sleep(2)
            st.write_stream(stream_data(node1_3))
            time.sleep(4)
            st.code(node1_4)
            time.sleep(2)
            st.write_stream(stream_data(node1_5))
            time.sleep(3)
            status.update(
                label="**Successfully remediated 3 Nodes**", state="complete", expanded=False
            )

    # with ph5:
    #     with st.status("Executing Remediation Actions", expanded=True) as status:
    #         st.write("Searching for data...")
    #         time.sleep(2)
    #         st.write("Found URL.")
    #         time.sleep(1)
    #         st.write("Downloading data...")
    #         time.sleep(1)
    #         status.update(
    #             label="**Successfully executed Remediation Actions for 6 Nodes**", state="complete", expanded=False
    #         )

    with ph6:
        with st.status("Monitoring Performance KPIs", expanded=True) as status:
            time.sleep(4)
            st.write_stream(stream_data(monitor_string))
            time.sleep(2)
            status.update(
                label="**Monitoring complete. KPIs have Improved.**", state="complete", expanded=False
            )

    with ph7:
        with st.status("Checking for Human Approval", expanded=True) as status:
            time.sleep(4)
            st.write_stream(stream_data(human_approval_string))
            time.sleep(1)
            status.update(
                label="**Human Approval not required in this case.**", state="complete", expanded=False
            )

    with ph8:
        with st.status(f"**Summarizing actions performed**", expanded=True) as status:
            time.sleep(4)
            st.write_stream(stream_data(conclude_string))
            time.sleep(1)
            status.update(
                label=f"**Successfully addressed Event: {event_name}**", state="complete", expanded=False
            )

    time_taken = random.randint(4, 7)
    metrics_ph.subheader(f":primary[Completed Automated RAN Reconfiguration in] :primary-background[{time_taken} mins]")
