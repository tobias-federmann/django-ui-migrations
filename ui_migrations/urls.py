"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.urls import include, path
	2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.db.models import Model
from dataclasses import dataclass
from typing import Literal

from .utils import get_urlpatterns, get_components_from_all_apps

urlpatterns = [
]

@dataclass
class ModelAccess:
	"""Access specifications for a model."""
	addable_by_roles: set[str]
	removable_by_roles: set[str]
	modifiable_by_roles: dict[str, set[str]]
	visible_by_roles: dict[str, set[str] | Literal[True]]


models_to_access: dict[type[Model], ModelAccess] = {}
for component, _ in get_components_from_all_apps():
	if component.model is None:
		continue

	# if the model is already in the dict, update the access specifications
	if model_acces := models_to_access.get(component.model):
		# update addable_by_roles
		model_acces.addable_by_roles.update(getattr(component, "addable_by_roles", set()))
		# update removable_by_roles
		model_acces.removable_by_roles.update(getattr(component, "removable_by_roles", set()))
		
		for field_options in getattr(component, "fields_options", []):
			# update modifiable_by_roles
			if model_acces.modifiable_by_roles.get(field_options.field_name):
				model_acces.modifiable_by_roles[field_options.field_name].update(getattr(field_options, "modifiable_by_roles", set()))
			else:
				model_acces.modifiable_by_roles[field_options.field_name] = getattr(field_options, "modifiable_by_roles", set())
			# update visible_by_roles
			if model_acces.visible_by_roles.get(field_options.field_name):
				if model_acces.visible_by_roles[field_options.field_name] == True:
					continue
				if getattr(field_options, "visible_by_roles", None) == True:
					model_acces.visible_by_roles[field_options.field_name] = True
					continue
				model_acces.visible_by_roles[field_options.field_name].update(getattr(field_options, "visible_by_roles", set())) # type: ignore
			else:
				model_acces.visible_by_roles[field_options.field_name] = getattr(field_options, "visible_by_roles", set())
	# if the model is not in the dict, add it
	else:
		models_to_access[component.model] = ModelAccess(
			addable_by_roles=set(getattr(component, "addable_by_roles", set())),
			removable_by_roles=set(getattr(component, "removable_by_roles", set())),
			modifiable_by_roles={
				field_options.field_name: set(field_options.modifiable_by_roles)
				for field_options in getattr(component, "fields_options", [])
				if hasattr(field_options, "modifiable_by_roles")
			},
			visible_by_roles={
				field_options.field_name: (True if field_options.visible_by_roles == True else set(field_options.visible_by_roles))
				for field_options in getattr(component, "fields_options", [])
				if hasattr(field_options, "visible_by_roles")
			},
		)


for model, model_access in models_to_access.items():
	# Create the REST endpoints and add their paths to the URLs
	urlpatterns.extend(get_urlpatterns(
		model,
		model_access.addable_by_roles,
		model_access.removable_by_roles,
		model_access.modifiable_by_roles,
		model_access.visible_by_roles
	))
