from app.agent.state import TRANSITIONS, can_transition
from app.enums import TERMINAL_STATUSES, InvestigationStatus as S


def test_happy_path_is_allowed():
    path = [S.CREATED, S.PLANNING, S.INVESTIGATING, S.SYNTHESIZING, S.AWAITING_APPROVAL, S.EXECUTING, S.VERIFYING, S.COMPLETED]
    assert all(can_transition(a, b) for a, b in zip(path, path[1:]))


def test_no_action_path_is_allowed():
    assert can_transition(S.SYNTHESIZING, S.COMPLETED)


def test_illegal_jumps_are_rejected():
    assert not can_transition(S.CREATED, S.EXECUTING)
    assert not can_transition(S.AWAITING_APPROVAL, S.VERIFYING)
    assert not can_transition(S.INVESTIGATING, S.EXECUTING)


def test_terminal_states_are_final():
    for status in TERMINAL_STATUSES:
        assert not TRANSITIONS.get(status)


def test_every_active_state_can_fail_cancel_or_time_out():
    for status, targets in TRANSITIONS.items():
        assert {S.FAILED, S.CANCELLED, S.TIMED_OUT} <= targets, status
