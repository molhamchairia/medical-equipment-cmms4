from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from core.rules import priority_for, validate_transition, current_window, inspection_policy

@pytest.mark.parametrize("risk,severity,expected", [
    ("very_high","stopped","P1"),("very_high","degraded","P1"),("very_high","cosmetic","P2"),
    ("high","stopped","P1"),("high","degraded","P2"),("high","cosmetic","P3"),
    ("medium","stopped","P2"),("medium","degraded","P3"),("medium","cosmetic","P4"),
    ("low","stopped","P3"),("low","degraded","P4"),("low","cosmetic","P4"),
])
def test_priority_matrix(risk,severity,expected): assert priority_for(risk,severity)==expected

@pytest.mark.parametrize("hour,minute,shift",[(6,59,"night"),(7,0,"morning"),(14,59,"morning"),(15,0,"evening"),(22,59,"evening"),(23,0,"night"),(0,30,"night"),(3,0,"night")])
def test_current_shift_window(hour,minute,shift):
    dt=datetime(2026,10,13,hour,minute,tzinfo=ZoneInfo("Asia/Damascus"))
    assert current_window(dt)[0]==shift

def test_night_window_starts_previous_day():
    dt=datetime(2026,10,13,1,30,tzinfo=ZoneInfo("Asia/Damascus"))
    _,start,end=current_window(dt)
    assert start.date().day==12 and end.date().day==13

def test_status_transition():
    validate_transition("operational","reported_faulty")
    with pytest.raises(ValueError): validate_transition("decommissioned","operational")

def test_inspection_policy():
    assert inspection_policy("very_high")=="per_shift"
    assert inspection_policy("high")=="daily"
    assert inspection_policy("low")=="none"
