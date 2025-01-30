import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from app.agent import Agent, AgentConfig
from app.models import IssueStatus
from app.llm_helper import Risk, RiskLevel, RiskAnalysis, ValidationResult

@pytest.fixture
def mock_managers():
    """Create mock instances of required managers"""
    return {
        'data_manager': Mock(
            get_events=AsyncMock(return_value=[
                Mock(dict=lambda: {"event_id": "test_event"})
            ]),
            get_event=AsyncMock(),
            create_issue=AsyncMock(return_value="test_issue_id"),
            get_issue=AsyncMock(),
            update_issue=AsyncMock(return_value=True)
        ),
        'network_manager': Mock(
            get_network_config_proposal=AsyncMock(return_value={"config": "test"}),
            run_network_config_proposal=AsyncMock(return_value=True)
        ),
        'notification_manager': Mock(
            send_notification=AsyncMock()
        ),
        'llm_helper': Mock(
            analyze_risk_pattern=AsyncMock(return_value=RiskAnalysis(
                identified_risks=[
                    Risk(
                        event_id="test_event",
                        node_id="test_node",
                        risk_level=RiskLevel.HIGH,
                        description="test description"
                    )
                ]
            )),
            validate_risk_assessment=AsyncMock(return_value=ValidationResult(
                is_valid=True,
                summary="test summary"
            )),
            evaluate_severity=AsyncMock(return_value=True)
        )
    }

@pytest.fixture
def agent(mock_managers):
    """Create Agent instance with mock managers"""
    config = AgentConfig(run_interval=1, lookback_period=24)
    return Agent(
        data_manager=mock_managers['data_manager'],
        network_manager=mock_managers['network_manager'],
        notification_manager=mock_managers['notification_manager'],
        llm_helper=mock_managers['llm_helper'],
        config=config
    )

@pytest.mark.asyncio
async def test_get_risks(agent, mock_managers):
    """Test risk analysis functionality"""
    risks = await agent._get_risks()

    assert len(risks) == 1
    assert isinstance(risks[0], Risk)
    assert risks[0].event_id == "test_event"
    mock_managers['data_manager'].get_events.assert_called_once()
    mock_managers['llm_helper'].analyze_risk_pattern.assert_called_once()

@pytest.mark.asyncio
async def test_process_risk_with_human_intervention(agent, mock_managers):
    """Test risk processing that requires human intervention"""
    risk = Risk(
        event_id="test_event",
        node_id="test_node",
        risk_level=RiskLevel.HIGH,
        description="test description"
    )

    await agent._process_risk(risk)

    # Verify the expected workflow
    mock_managers['data_manager'].create_issue.assert_called_once()
    mock_managers['notification_manager'].send_notification.assert_called_once_with("test_issue_id")
    assert mock_managers['data_manager'].update_issue.call_count >= 1

@pytest.mark.asyncio
async def test_process_risk_without_human_intervention(agent, mock_managers):
    """Test risk processing without human intervention"""
    # Configure for automatic handling
    mock_managers['llm_helper'].evaluate_severity.return_value = False
    risk = Risk(
        event_id="test_event",
        node_id="test_node",
        risk_level=RiskLevel.LOW,
        description="test description"
    )

    await agent._process_risk(risk)

    # Verify automatic resolution path
    mock_managers['network_manager'].run_network_config_proposal.assert_called_once()
    mock_managers['notification_manager'].send_notification.assert_not_called()

@pytest.mark.asyncio
async def test_agent_lifecycle(agent):
    """Test agent start and stop functionality"""
    await agent.start()
    assert agent._task is not None

    await agent.stop()
    assert agent._task is None

@pytest.mark.asyncio
async def test_failed_config_generation(agent, mock_managers):
    """Test handling of failed configuration generation"""
    mock_managers['network_manager'].get_network_config_proposal.return_value = None
    risk = Risk(
        event_id="test_event",
        node_id="test_node",
        risk_level=RiskLevel.MEDIUM,
        description="test description"
    )

    await agent._process_risk(risk)

    # Verify failure handling
    last_call = mock_managers['data_manager'].update_issue.call_args
    assert last_call[0][1]['status'] == IssueStatus.FAILED.value
    assert "Failed to generate network configuration" in last_call[0][1]['summary']
