from app.jobs.connectors import default_connectors


def test_default_connectors_registers_mock_remotive_and_remote_rocketship() -> None:
    names = [connector.name for connector in default_connectors()]
    assert {"mock", "remotive", "remote_rocketship"} <= set(names)
    assert len(names) == len(set(names))  # names must stay unique: source resolution is by name
