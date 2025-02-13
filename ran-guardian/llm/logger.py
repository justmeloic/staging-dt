import os
from typing import Optional
from google.cloud import storage
from datetime import datetime
import pytz

timezone = pytz.timezone("CET")


class AgentWorkflowLogger:
    def __init__(
        self,
        bucket_name: str,
        logs_location: str,
        issue_id: str,
        node_id: str,
        agent_name: str,
    ):
        """
        Initialize the workflow logger.

        Args:
            issue_id (str): Unique identifier for the issue
            bucket_name (str): The GCS bucket name
            logs_location (str): The location (folder) within the bucket
            agent_name (str): Name of the agent performing the task
        """
        self.issue_id = issue_id
        self.agent_name = agent_name
        self.bucket_name = bucket_name  # Replace with your actual bucket name
        self.logs_location = logs_location
        self.blob_name = f"{logs_location}/{issue_id}_{node_id}.log"

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)

        self.log_buffer = []

    def log(self, message: str) -> None:
        """
        Append a log message to the log buffer

        Args:
            message (str): The message to be logged
        """
        current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

        # Format the log entry
        log_entry = (
            f"[{current_time}] [{self.issue_id}] [{self.agent_name}] {message}\n"
        )

        self.log_buffer.append(log_entry)

    def save_to_gcs(self) -> None:
        """Write the log buffer to GCS, appending to existing issue log"""
        if not self.log_buffer:
            return

        log_lines = "\n".join(self.log_buffer)
        try:
            # Get the blob (file) from the bucket
            blob = self.bucket.blob(self.blob_name)

            # If the file exists, download current content
            if blob.exists():
                current_content = blob.download_as_text()
                updated_content = current_content + log_lines
            else:
                updated_content = log_lines

            # Upload the updated content
            blob.upload_from_string(updated_content)

            self.log_buffer = []  # Clear the buffer after writing

        except Exception as e:
            raise Exception(f"Failed to write to log file: {str(e)}")
