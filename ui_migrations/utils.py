from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from django.urls import path, URLPattern
from django.db import models
from django.db.models.fields import related
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from typing import Literal
from .components import UiComponent



def get_urlpatterns(
		model: type[models.Model],
		addable_by_roles: set[str],
		removable_by_roles: set[str],
		modifiable_by_roles: dict[str, set[str]],
		visible_by_roles: dict[str, set[str] | Literal[True]],
) -> list[URLPattern]:
	"""Create REST endpoints for the model and return their paths"""
	def get_serializer(_model: type[models.Model], _fields: list[str]) -> type[serializers.ModelSerializer]:
		"""Create a serializer for the model with the given fields."""
		class Serializer(serializers.ModelSerializer):
			class Meta:
				model = _model
				fields = _fields + ["pk"]
				depth = 1
			def update(self, instance: models.Model, validated_data: dict):
				for field, value in validated_data.items():
					if isinstance(value, list):
						for item in value:
							id = item.pop("pk", None)
							related_model: models.Model = getattr(instance, field).model
							if id:
								related_instance = related_model.objects.filter(id=id).first()
								if related_instance:
									for key, val in item.items():
										setattr(related_instance, key, val)
									related_instance.save()
					else:
						setattr(instance, field, value)
				instance.save()
				return instance
		return Serializer
	
	def get_item_view(request: Request, pk: int):
		"""Get a single item."""

		user: User = request.user
		# URL query of the form ?_fields=id,name,price
		query_params = {key: (value[0] if isinstance(value, list) else value) for key, value in request.query_params.dict().items()}
		fields_str = query_params.pop("_fields", "")
		# remove the format query parameter if it exists
		query_params.pop("format", None)
		fields = fields_str.split(",") if fields_str else []
		
		# check if the user has permission to view the fields
		for field in fields:
			field_visible_by_roles = visible_by_roles.get(field, [])
			if (not field_visible_by_roles == True) and (not user.groups.filter(name__in=field_visible_by_roles).exists()):
				return Response(status=403, data={"error": f"User does not have permission to view field {field}."})
		
		item = model.objects.filter(pk=pk).first()
		Serializer = get_serializer(model, fields)
		return Response(data=Serializer(item).data if item else {})
	

	def post_item_view(request: Request):
		"""Create a new item."""

		user: User = request.user
		# check if the user has permission to add items
		if not user.groups.filter(name__in=addable_by_roles).exists():
			return Response(status=403, data={"error": "User does not have permission to add items."})
		
		Serializer = get_serializer(model, [field.name for field in model._meta.fields])
		serializer = Serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		created_item = serializer.save()
		return Response(data=Serializer(created_item).data)
	

	def patch_item_view(request: Request, pk: int):
		"""Update an existing item."""

		user: User = request.user
		# check if the user has permission to modify the fields of the item
		for field in request.data.keys(): # type: ignore
			if not user.groups.filter(name__in=modifiable_by_roles.get(field, [])).exists():
				return Response(status=403, data={"error": f"User does not have permission to modify field {field}."})
		
		Serializer = get_serializer(model, [field.name for field in model._meta.fields])
		serializer = Serializer(model.objects.filter(pk=pk).first(), data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		updated_item = serializer.save()
		return Response(data=Serializer(updated_item).data)
	

	def delete_item_view(request: Request, pk: int):
		"""Delete an existing item."""

		user: User = request.user
		# check if the user has permission to remove items
		if not user.groups.filter(name__in=removable_by_roles).exists():
			return Response(status=403, data={"error": "User does not have permission to remove items."})
		
		model.objects.filter(pk=pk).delete()
		return Response(status=204)
	

	@api_view(['GET', 'PATCH', 'DELETE'])
	def item_view(request: Request, pk: int):
		"""Get, create, update or delete a single item."""
		match request.method:
			case 'GET':
				return get_item_view(request, pk)
			case 'PATCH':
				return patch_item_view(request, pk)
			case 'DELETE':
				return delete_item_view(request, pk)
	

	def get_items_view(request: Request):
		"""Get multiple items consisting of the given _fields and matching the filter query."""
		user: User = request.user

		query_params = {key: (value[0] if isinstance(value, list) else value) for key, value in request.query_params.dict().items()}
		fields_str = query_params.pop("_fields", "")
		sort_by = query_params.pop("_sortBy", None)
		sort_dir = query_params.pop("_sortDir", None)
		page_number = int(query_params.pop("_page", 1))
		page_size = int(query_params.pop("_pageSize", 10))
		# remove the format query parameter if it exists
		query_params.pop("format", None)
		# get the fields to be included in the response
		fields = fields_str.split(",") if fields_str else []

		# check if the user has permission to view the fields
		for field in fields:
			field_visible_by_roles = visible_by_roles.get(field, [])
			if (not field_visible_by_roles == True) and (not user.groups.filter(name__in=field_visible_by_roles).exists()):
				return Response(status=403, data={"error": f"User does not have permission to view field {field}."})

		query_set = model.objects.filter(**query_params).order_by(("-" if sort_dir == "desc" else "") + (sort_by if sort_by else "pk"))
		paginator = Paginator(query_set, page_size)
		page = paginator.get_page(page_number)
		# create a serializer for the model with the given fields
		Serializer = get_serializer(model, fields)
		return Response(data={
			"items": [Serializer(item).data for item in page],
			"totalItems": paginator.count,
			"totalPages": paginator.num_pages,
			"page": page_number,
		})
	
	@api_view(['GET', 'POST'])
	def items_view(request: Request):
		"""Get all items or create a new item."""
		match request.method:
			case 'GET':
				return get_items_view(request)
			case 'POST':
				return post_item_view(request)

	# Create URL patterns for the model using the name of the model:
	# one for getting a single item and one for getting multiple items
	return [
		path(f"{model.__name__.lower()}s/<int:pk>", item_view),
		path(f"{model.__name__.lower()}s", items_view),
	]


def get_components_from_all_apps() -> set[tuple[UiComponent, str]]:
	"""Get all UI components from all apps with the path to their frontend as tuples."""
	from django.apps import apps
	import importlib
	components_and_paths = set()
	for app_config in apps.get_app_configs():
		try:
			ui_components_module = importlib.import_module(f"{app_config.name}.ui_components")
			for component in ui_components_module.components:
				components_and_paths.add((component, ui_components_module.frontends[component.ui_framework]))
		except ModuleNotFoundError:
			pass
	return components_and_paths
