import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request

# copy paste from app.models
from google.cloud import bigquery
from google.cloud.bigquery import enums
from pydantic import BaseModel, Field

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID")

# configuaration of the mock data's behavior
TIME_INTERVAL = int(os.getenv("TIME_INTERVAL"))
EVENT_PROBA = float(os.getenv("EVENT_PROBA"))


logger = logging.getLogger(__name__)
router = APIRouter()

bq_client = bigquery.Client(project=PROJECT_ID, location="europe-west3")


# -------------------
# data types
# -------------------


class PerformanceData(BaseModel):
    # metric names have been modified: "4G_ERI" are removed from the original column name
    node_id: str
    timestamp: datetime
    Max_RRC_Conn_User: float
    RRC_Estab_SR_pct: float
    eRAB_SSR_VoLTE_pct: float
    eRAB_SSR_Data_pct: float
    Traffic_Data_Vol_DL_MiB: float
    Traffic_Data_Vol_UL_MiB: float
    # Various performance metrics


class Alarm(BaseModel):
    alarm_id: str
    node_id: str
    event_id: Optional[str]
    created_at: datetime
    cleared_at: Optional[datetime] = None
    alarm_type: str
    description: str


class NodeTimeRange(BaseModel):
    node_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# -------------------
# utility functions
# -------------------


def _shake(x, mode: str = "pct"):
    ratio = np.random.rand() * 0.2 + 0.9
    if mode == "pct":
        return np.clip(x * ratio, 0, 1)
    elif mode == "int":
        return int(x * ratio)
    elif mode == "float":
        return float(x * ratio)
    else:
        raise Exception("mode not implemented !")


def _parse_node_id(node_id: str):
    try:
        node_id = int(node_id)
        node_id = f"{node_id}.0"
        return node_id
    except ValueError:
        try:
            node_id = float(node_id)
            node_id = f"{node_id:8.1f}"
            return node_id
        except ValueError:
            logger.warning(
                "node_id may not be well formated! It should be a string of 8 digit number (it may has a trailling .0)"
            )
    finally:
        return node_id


def _parse_node_time_range(node_time_range: NodeTimeRange):
    node_id = _parse_node_id(node_time_range.node_id)
    start_time = node_time_range.start_time
    end_time = node_time_range.end_time

    if (end_time is None) and (start_time is None):
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=TIME_INTERVAL)
    elif end_time is None:
        end_time = start_time + timedelta(minutes=TIME_INTERVAL)
    elif start_time is None:
        start_time = end_time - timedelta(minutes=TIME_INTERVAL)
    return node_id, start_time, end_time


def _run_query_job(node_id: str, hour_list: List[int], with_node=True):
    table_name = "perf-summary" if with_node else "perf-summary-mean"
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{BQ_DATASET_ID}.{table_name}`
        WHERE hour IN UNNEST(@hour_list)
    """
    query_parameters = [
        bigquery.ArrayQueryParameter("hour_list", enums.SqlTypeNames.INT64, hour_list),
    ]
    if with_node:
        query += f" AND `OSS-NodeID_Generic` = @oss_node_id"
        query_parameters.append(
            bigquery.ScalarQueryParameter("oss_node_id", "FLOAT64", node_id)
        )

    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    job = bq_client.query(query, job_config=job_config)
    return job


# -------------------
# end point definition
# -------------------


@router.post("/performances", response_model=List[PerformanceData])  # Type hint
async def get_performance(
    node_time_range: NodeTimeRange,
):
    """
    Generate mock performance data based on real hourly every data of the node from the provided performance data
    If the node cannot be found, then the mean across all nodes will be used to generate fake data
    """
    node_id, start_time, end_time = _parse_node_time_range(node_time_range)

    # Round up start_time to the next quarter hour
    remainder = start_time.minute % TIME_INTERVAL
    if remainder != 0:
        start_time += timedelta(
            minutes=(TIME_INTERVAL - remainder), seconds=start_time.second
        )
        if start_time > end_time:
            return []

    # Create a pandas DatetimeIndex with quarter-minute frequency
    time_range = pd.date_range(
        start=start_time, end=end_time, freq=f"{TIME_INTERVAL}min"
    )
    hour_list = [t.hour for t in time_range]

    query_job = _run_query_job(
        node_id=node_id, hour_list=hour_list, with_node=isinstance(node_id, float)
    )
    try:
        query_result = query_job.result()
        if query_result.total_rows == 0:
            # if the node_id does not exist in the current data, then run a query which is node_id independent
            query_job = _run_query_job(
                node_id=node_id, hour_list=hour_list, with_node=False
            )
            query_result = query_job.result()

        result_dict = {}
        for row in query_result:
            row_dict = dict(row)
            result_dict[row_dict["hour"]] = row_dict

        perf_data = []

        for time in time_range:
            hour = time.hour
            perf = result_dict.get(hour, {})
            perf_data.append(
                PerformanceData(
                    node_id=str(node_id),
                    timestamp=time,
                    Max_RRC_Conn_User=_shake(
                        perf.get("4G_ERI_Max_RRC_Conn_User"), mode="int"
                    ),
                    RRC_Estab_SR_pct=_shake(
                        perf.get("4G_ERI_RRC_Estab_SR_pct"), mode="pct"
                    ),
                    eRAB_SSR_VoLTE_pct=_shake(
                        perf.get("4G_ERI_eRAB_SSR_VoLTE_pct"), mode="pct"
                    ),
                    eRAB_SSR_Data_pct=_shake(
                        perf.get("4G_ERI_eRAB_SSR_Data_pct"), mode="pct"
                    ),
                    Traffic_Data_Vol_DL_MiB=_shake(
                        perf.get("4G_ERI_Traffic_Data_Vol_DL_MiB"), mode="float"
                    ),
                    Traffic_Data_Vol_UL_MiB=_shake(
                        perf.get("4G_ERI_Traffic_Data_Vol_UL_MiB"), mode="float"
                    ),
                )
            )
        return perf_data

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_row_num(node_id: str, start_time: datetime, end_time: datetime):
    start_time_str = start_time.strftime("%Y-%m-%d")  # only use start date
    combined_str = f"{node_id}|{start_time_str}"
    hashed_bytes = hashlib.sha256(combined_str.encode("utf-8")).digest()
    row_num = (
        int.from_bytes(hashed_bytes[:8], byteorder="big", signed=False) % 497
    )  # hard coded total row number
    return row_num


@router.post("/alarms", response_model=List[Alarm])  # Type hint
async def get_alarms(node_time_range: NodeTimeRange):
    # here the alarm data should be issued by site id
    node_id, start_time, end_time = _parse_node_time_range(node_time_range)

    row_num = _generate_row_num(node_id, start_time, end_time)

    if np.random.rand() > EVENT_PROBA:
        # no alarm for the node
        return []
    n_row = row_num % 3  # choose max 3 rows
    query = f"""
        SELECT *
        FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY EVENTTIME) AS row_num
        FROM
            `{PROJECT_ID}.ran_guardian.alarm`
        )
        WHERE row_num between {row_num} and {row_num + n_row};
    """
    # Note: we mock the data by randomly select one
    try:
        query_job = bq_client.query(query)
        alarm_data = []

        time_range = pd.date_range(start=start_time, end=end_time, freq=f"1D")

        for row in query_job.result():
            row_dict = dict(row)
            idx = np.random.choice(range(len(time_range)))
            alarm_data.append(
                Alarm(
                    alarm_id=row_dict.get("ALERTKEY"),
                    node_id=node_id,
                    event_id=row_dict.get("EVENT_ID"),
                    created_at=time_range[idx].to_pydatetime(),
                    cleared_at=None,
                    alarm_type=row_dict.get("ALERTGROUP"),
                    description=row_dict.get("SUMMARY")
                    + "\n"
                    + row_dict.get("ADDITIONALTEXT"),
                )
            )

        return alarm_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
