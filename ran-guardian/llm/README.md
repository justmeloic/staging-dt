# LLM Agent 
This module implements the agentic AI module of the RAN guardian solution. It consists of a multi-agent workflow where a main, supervisor ("reasoning") agent is responsible for overseeing the overall remediation plan, while other task-specific agents are responsible each for a specific network configuration action (e.g. "activate MLB", "deactivate CA", etc.)

The following diagram illustrates the agent architecture:
![](../assets/agent_arch.jpg)

The workflow was implemented using LangGraph. 

## Testing the agent (in isolation)
If you want to run a test end-to-end workflow, run the provided sample code:

```
poetry run python examples/sample_workflow.py
```

You should see the outputs in a log file called `agent.log` in the local directory. 