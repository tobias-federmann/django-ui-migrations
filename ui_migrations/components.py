from abc import ABC
from typing import Literal, OrderedDict, Any
from typing_extensions import TypedDict, NotRequired
import dataclasses

from django.db import models
from django.template.loader import render_to_string

from .ui_frameworks import UiFramework
from .actions import Action


SerializedComponent = str


def get_field_input_type(field_internal_type: str, field_choices: list | None = None) -> str:
	"""Get the type of the input element for a field."""
	if field_choices:
		return "select"
	match field_internal_type:
		case "AutoField" | "BigAutoField" | "DecimalField" | "FloatField" | "IntegerField" | "PositiveIntegerField" | "PositiveSmallIntegerField" | "SmallAutoField" | "SmallIntegerField":
			return "number"
		case "BooleanField" | "NullBooleanField":
			return "checkbox"
		case "DateField":
			return "date"
		case "DateTimeField":
			return "datetime-local"
		case "DurationField" | "TimeField":
			return "time"
		case "EmailField":
			return "email"
		case "FileField":
			return "file"
		case "TextField":
			return "textarea"
		case "URLField":
			return "url"
		case "CharField" | "FilePathField" | "GenericIPAddressField" | "SlugField" | "UUIDField" | _:
			return "text"


@dataclasses.dataclass
class CustomComponentOptions:
	"""Options for a custom component that should be shown in a field of a UI component."""
	component_name: str
	prop_name: str

@dataclasses.dataclass
class ActionOptions:
	"""Options for an action that can be performed on items."""
	display_name: str
	roles: list[str]
	actions: list[Action]


class UiComponent(ABC):
	"""Abstract base class for any UI Component"""
	model: type[models.Model] | None
	"""The class of the corresponding Django model"""
	styling: bool = True
	"""Wether to generate basic styling for this component"""
	def __init__(self, name: str | None = None, *, ui_framework: UiFramework):
		"""Initialize this component with a `name`, which is used as the concrete component name in the UI framework, and the `ui_framework` that this component should be generated for."""
		self.name = name or self.__class__.__name__
		self.ui_framework = ui_framework
	def generate(self) -> SerializedComponent:
		"""Generate the component."""
		...

class DataTable(UiComponent):
	"""Component type `DataTable`. Inherit from this class for declaring a table component."""

	model: type[models.Model]

	max_items_per_page: int = 100
	"""How many items to show per table page (for pagination)"""

	addable_by_roles: list[str] = []
	"""Which roles are allowed to create new items in this component"""

	removable_by_roles: list[str] = []
	"""Which roles are allowed to remove items in this component"""

	@dataclasses.dataclass
	class FieldOptions:
		"""Options for a field that should be shown in a DataTable for every item."""
		field_name: str
		"""Name of the field from the model"""
		display_name: str | None = None
		"""Name that is displayed in the UI"""
		link: str | None = None
		"""Link that should be opened when the field is clicked, use `{field_name}` to dynamically insert the item's value at the field"""
		sortable: bool = False
		"""Wether one can sort by this field"""
		modifiable_by_roles: list[str] = dataclasses.field(default_factory=list)
		"""Which roles are allowed to modify this fields's contents"""
		visible_by_roles: list[str] | Literal[True] = True
		"""Which roles are allowed to this field's contents (or `true` if all roles are allowed to)"""
		auto_generated: bool = False
		"""Wether this field's value is automatically generated when creating a new item (for example an `id` field that is automatically assigned by the database)"""
		custom_components_options: list[CustomComponentOptions] = dataclasses.field(default_factory=list)
		"""list of options for custom components that should be inserted into this field"""
 
	fields_options: list[FieldOptions]
	"""Options for the fields that should be shown in the DataTable."""

	actions_options: list[ActionOptions] = []
	"""Actions that can be performed on the items of the DataTable."""

	def __init__(self, name: str | None = None, *, ui_framework: UiFramework):
		super().__init__(name, ui_framework=ui_framework)
		
		# Get the choices for the fields from the model to make them passable to the template
		self.fields_choices: dict[str, list] = {}
		for field_name in (field_options.field_name for field_options in self.fields_options):
			if choices := getattr(self.model._meta.get_field(field_name), "choices", None):
				self.fields_choices[field_name] = [choice[0] for choice in choices] # type: ignore
		
		# Get the input types for the fields from the model (for different kinds of html input elements) to make them passable to the template
		self.fields_input_types: dict[str, str] = {}
		for field_name in (field_options.field_name for field_options in self.fields_options):
			self.fields_input_types[field_name] = get_field_input_type(self.model._meta.get_field(field_name).get_internal_type(), self.fields_choices.get(field_name))

	def generate(self) -> SerializedComponent:
		match self.ui_framework:
			case UiFramework.VUE:
				# Pass properties to the Jinja 2 template
				return render_to_string("vue/DataTable.html.j2", {
					"fields_options": self.fields_options,
					"model_name": self.model.__name__.lower(),
					"addable_by_roles": self.addable_by_roles,
					"removable_by_roles": self.removable_by_roles,
					"max_items_per_page": self.max_items_per_page,
					"actions_options": self.actions_options,
					"fields_choices": self.fields_choices,
					"fields_input_types": self.fields_input_types,
					"styling": self.styling,
				}, using="jinja2")
			case f:
				raise NotImplementedError(f"UI Framework '{f}' is not yet supported.")


class DataEntry(UiComponent):
	model: type[models.Model]

	@dataclasses.dataclass
	class FieldOptions:
		"""Options for a field that should be shown in a DataEntry."""
		field_name: str
		"""Name of the field from the model"""
		display_name: str | None = None
		"""Name that is displayed in the UI"""
		modifiable_by_roles: list[str] = dataclasses.field(default_factory=list)
		"""Which roles are allowed to modify this field's content"""
		visible_by_roles: list[str] | Literal[True] = True
		"""Which roles are allowed to see this field's conten (`True` if all roles are allowed to)"""
		custom_components_options: list[CustomComponentOptions] = dataclasses.field(default_factory=list)
		"""List of options for custom components that should be inserted into this field"""
		fields_options: list["DataEntry.FieldOptions"] = dataclasses.field(default_factory=list)
		"""Nested fields for nested data (as in foreign key relationships)"""

	fields_options: list[FieldOptions]
	"""Options for the fields that should be shown in the DataTable."""

	actions_options: list[ActionOptions] = []
	"""Actions that can be performed on the items of the DataTable."""

	data_by_prop: str | None = None
	"""The name of the prop that contains the data for the DataEntry. If None, data is fetched from within the component."""
 
	def __init__(self, name: str | None = None, *, ui_framework: UiFramework):
		super().__init__(name, ui_framework=ui_framework)
		
		# Get the choices for the fields from the model to make them passable to the template
		self.fields_choices: dict[str, list] = {}
		for field_name in (field_options.field_name for field_options in self.fields_options):
			if choices := getattr(self.model._meta.get_field(field_name), "choices", None):
				self.fields_choices[field_name] = [choice[0] for choice in choices] # type: ignore
		
		# Get the input types for the fields from the model (for different kinds of html input elements) to make them passable to the template
		self.fields_input_types: dict[str, str] = {}
		for field_name in (field_options.field_name for field_options in self.fields_options):
			self.fields_input_types[field_name] = get_field_input_type(self.model._meta.get_field(field_name).get_internal_type(), self.fields_choices.get(field_name))
 
	def generate(self) -> SerializedComponent:
		match self.ui_framework:
			case UiFramework.VUE:
				# Pass properties to the Jinja 2 template
				return render_to_string("vue/DataEntry.html.j2", {
					"fields_options": self.fields_options,
					"model_name": self.model.__name__.lower(),
					"actions_options": self.actions_options,
					"fields_choices": self.fields_choices,
					"fields_input_types": self.fields_input_types,
					"data_by_prop": self.data_by_prop,
					"styling": self.styling,
				}, using="jinja2")
			case f:
				raise NotImplementedError(f"UI Framework '{f}' is not yet supported.")
