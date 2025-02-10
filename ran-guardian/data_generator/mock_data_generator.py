import random

import numpy as np
import pandas as pd
from google.cloud import firestore, storage

BUCKET_ID = "ran-guardian-data"


class MockDataGenerator:
    def __init__(self, config):
        client = storage.Client()
        bucket = client.bucket(BUCKET_ID)
        perf_summary = bucket.blob("perf_summary.parquet")
        pass

    def run(self):
        # generate mock data
        ...
