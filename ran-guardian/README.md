# Setup

Create a .env file with the following keys:

```
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
```

In addition, configure the environment variables specified in `.env.example`.

Install dependencies
```
poetry install
```

# Create People Events DB

```
poetry run python ran_guardian/run_event_scout.py
poetry run python ran_guardian/run_event_scout.py
```

# Set up Events Explorer UI as a Cloud Run service
```
gcloud builds submit --tag gcr.io/[PROJECT_NAME]/[REPO_NAME]/events-explorer-ui:latest .
```
```
gcloud run deploy events-explorer-ui \
    --image gcr.io/[PROJECT_NAME]/[REPO_NAME]/events-explorer-ui:latest \
    --platform managed \
    --region europe-west1 \
    --port 8501 \
    --set-env-vars GOOGLE_APPLICATION_CREDENTIALS_CONTENT="$(base64 ../events_explorer_key.json)" \
    --set-env-vars KEY1=VALUE1,KEY2=VALUE2
```

# Run FastAPI for mock data server
In another terminal
```
poetry run uvicorn data_generator.main:app --reload --port 8001
```
# Run FastAPI for mock data server
In another terminal
```
poetry run uvicorn data_generator.main:app --reload --port 8001
```

# Run FastAPI for backend
First in one terminal start the server
```
poetry run uvicorn app.main:app --reload
```

Browse and try API routes at `http://localhost:8000/docs`

The following is a sample payload response to a `GET http://localhost:8080/issues/{issue_id}`:

```json
{
    "event": {
      "event_id": "0gcVnsqRH2460IQ1lTud",
      "location": {
        "latitude": 48.9471455,
        "longitude": 9.434181299999999,
        "address": "Backnang, Baden-Württemberg"
      },
      "start_date": "2025-10-03T00:00:00",
      "end_date": "2025-10-03T00:00:00",
      "name": "Day of German Unity",
      "url": "[1, 2, 3, 4, 5, 7, 8, 9]",
      "event_type": "Public Holiday Celebration",
      "size": "M",
      "issue_id": "0gcVnsqRH2460IQ1lTud"
    },
    "issue": {
      "issue_id": "0gcVnsqRH2460IQ1lTud",
      "event_id": "0gcVnsqRH2460IQ1lTud",
      "event_risk": {
        "event_id": "0gcVnsqRH2460IQ1lTud",
        "node_summaries": [
          {
            "node_id": "64879507",
            "site_id": "BY6293",
            "capacity": 131,
            "timestamp": "2025-02-11T21:22:58.043206+00:00",
            "performances": [
              {
                "node_id": "64879507.0",
                "timestamp": "2025-02-11T20:31:52.473051+00:00",
                "rrc_max_users": 14,
                "rrc_setup_sr_pct": 0.9930432604762188
              },
              {
                "node_id": "64879507.0",
                "timestamp": "2025-02-11T20:46:52.473051+00:00",
                "rrc_max_users": 12,
                "rrc_setup_sr_pct": 1
              },
              {
                "node_id": "64879507.0",
                "timestamp": "2025-02-11T21:01:52.473051+00:00",
                "rrc_max_users": 11,
                "rrc_setup_sr_pct": 1
              },
              {
                "node_id": "64879507.0",
                "timestamp": "2025-02-11T21:16:52.473051+00:00",
                "rrc_max_users": 12,
                "rrc_setup_sr_pct": 1
              }
            ],
            "alarms": [
              {
                "alarm_id": "MD=CISCO_EPNM!ND=49_2373_58_71J1_CSG.t.de!FTP=name=GigabitEthernet0/0/0/1.4094;lr=lr-gigabit-ethernet",
                "node_id": "BY6293",
                "event_id": "43 008 479",
                "created_at": "2025-02-11T21:07:57.316534+00:00",
                "cleared_at": null,
                "alarm_type": "Switches and Routers",
                "description": "LINK_DOWN\n10.121.133.70;Port GigabitEthernet0/0/0/1.4094 (Description: ***dummy interface for storm control***) is down on device 10.121.133.70._LINK_DOWNIRPM_PORTKARTE_SLOT_NR = DefIRPM_PORTKARTE_SLOT_NR = DefIRPM_PORTKARTE_SLOT_NR = Def"
              },
              {
                "alarm_id": "60011",
                "node_id": "BY6293",
                "event_id": "43 378 923",
                "created_at": "2025-02-11T21:07:57.316534+00:00",
                "cleared_at": null,
                "alarm_type": "ANDREW",
                "description": "RFD Port RSSI Low (Port 2)\n10.90.119.3_17676366_60011_RFD Port RSSI Low (Port 2)_OMC=1.IONE=57.CAN=1.RFD=15_40021912_SY4213_SY_S-Mercedes-Benz Arena SY4213 MU-9_OMC=1.IONE=57.CAN=1.RFD=15_.1.3.6.1.4.1.6408.201.3.4.13.1.4.262001.63064463.17676366"
              }
            ],
            "is_problematic": false,
            "summary": ""
          },
          {
            "node_id": "64879263",
            "site_id": "BY6293",
            "capacity": 212,
            "timestamp": "2025-02-11T21:22:59.408488+00:00",
            "performances": [
              {
                "node_id": "64879263.0",
                "timestamp": "2025-02-11T20:31:56.043635+00:00",
                "rrc_max_users": 14,
                "rrc_setup_sr_pct": 1
              },
              {
                "node_id": "64879263.0",
                "timestamp": "2025-02-11T20:46:56.043635+00:00",
                "rrc_max_users": 13,
                "rrc_setup_sr_pct": 0.9568385184139592
              },
              {
                "node_id": "64879263.0",
                "timestamp": "2025-02-11T21:01:56.043635+00:00",
                "rrc_max_users": 12,
                "rrc_setup_sr_pct": 1
              },
              {
                "node_id": "64879263.0",
                "timestamp": "2025-02-11T21:16:56.043635+00:00",
                "rrc_max_users": 11,
                "rrc_setup_sr_pct": 0.9592122707513902
              }
            ],
            "alarms": [
              {
                "alarm_id": "COMMUNICATION",
                "node_id": "BY6293",
                "event_id": "43 370 934",
                "created_at": "2025-02-11T21:07:58.637962+00:00",
                "cleared_at": null,
                "alarm_type": "amf",
                "description": "CN_COMBO_Core_5GC-Mavenir: Connection to ANID is restored - Connection restored\nt5g-1.az.gp,ManagedElement=me-mtcil1,NetworkFunction=t5g1azgpamf1,NFService=amf-n2iwf,NFServiceInstance=amf-n2iwf-5b9fcbd55f-n7b8v,id=62f2101104f29622,ipv4Address=10.109.148.224,peer-info-type=GNB,"
              },
              {
                "alarm_id": "60011",
                "node_id": "BY6293",
                "event_id": "43 378 923",
                "created_at": "2025-02-11T21:07:58.637962+00:00",
                "cleared_at": null,
                "alarm_type": "ANDREW",
                "description": "RFD Port RSSI Low (Port 4)\n10.90.119.4_17109727_60011_RFD Port RSSI Low (Port 4)_OMC=1.IONE=14.CAN=1.WIN=105.RFD=16_40019299_DO_Dortmund-U-Bahn 270 MU_OMC=1.IONE=14.CAN=1.WIN=105.RFD=16_.1.3.6.1.4.1.6408.201.3.4.13.1.4.262001.60791689.17109727"
              },
              {
                "alarm_id": "25000",
                "node_id": "BY6293",
                "event_id": "43 378 923",
                "created_at": "2025-02-11T21:07:58.637962+00:00",
                "cleared_at": null,
                "alarm_type": "ANDREW",
                "description": "Slot 1 Group 1 UL Antenna Isolation Alarm\n10.90.119.5_16970593_25000_Slot 1 Group 1 UL Antenna Isolation Alarm_OMC=1.NODA=835_40006200_MY_M_Unterbiberg_R6968_1_00.d0.ac.e1.fb.c7_.1.3.6.1.4.1.6408.201.3.4.13.1.4.262001.60239595.16970593"
              }
            ],
            "is_problematic": false,
            "summary": ""
          }
        ],
        "risk_level": "high",
        "description": "mock description"
      },
      "node_ids": [],
      "status": "new",
      "created_at": "2025-02-11T21:22:59.656319+00:00",
      "updated_at": "2025-02-11T21:22:59.656352+00:00",
      "updates": [],
      "summary": "mock summary",
      "tasks": null
    }
  }
```
