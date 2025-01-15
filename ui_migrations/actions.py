from abc import ABC
from typing import Literal, Any
from dataclasses import dataclass, field


@dataclass
class Action(ABC):
	"""Abstract base class for an triggerable action"""
	_type: str
	"""Type of the action (statically set by the subclasses)"""


@dataclass
class IterateAction(Action):
	"""Iterate over the choices of a field."""
	field_name: str
	direction: Literal["forward", "backward"] = "forward"
	_type: str = field(default="iterate", init=False)

@dataclass
class ToggleAction(Action):
	"""Switch between TRUE and FALSE of a field."""
	field_name: str
	_type: str = field(default="toggle", init=False)

@dataclass
class OpenUrlAction(Action):
	"""Open a URL. Can contain a field name in curly braces to insert the value of the field in the URL."""
	url: str
	new_tab: bool = True
	_type: str = field(default="open_url", init=False)

@dataclass
class SetCurrentDateAction(Action):
	"""Set the current date on a date time field."""
	field_name: str
	_type: str = field(default="set_current_date", init=False)
