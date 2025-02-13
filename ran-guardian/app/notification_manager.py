from typing import Dict, Optional


class NotificationManager:
    
    async def send_notification(self, issue_id: str) -> Dict:
        ...