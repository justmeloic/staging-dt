from typing import Dict, Optional

class NetworkConfigManager:
    async def get_network_config_proposal(self, issue_id: str) -> Dict:
        return {}
       # ... logic to generate network config proposal ...

    async def run_network_config_proposal(self, proposal_id: str, config: Optional[dict] = None) -> Dict:
        return {}
        ...
        # ... logic to apply the configuration ...


