# Django UI Migrations

The repository contains a Django app called `ui_migrations`, that adds the functionality to a Django project to declare UI components based on Django models, migrate them to a frontend framework of choice (only Vue.js currently supported) and autoatically create REST endpoints for communication with the Django backend.

## How To Use

* Add the `ui_migrations` package as app to the Django project
* Add `"ui_migrations"` to `INSTALLED_APPS` in `settings.py` of your project directory
* Add `path("", include("ui_migrations.urls"))` to `urlpatterns` in `urls.py` of your project directory
* Create a `ui_components.py` file in the app that you want to create UI components for
* In this file, declare components as classes, as seen in the example later, and set up paths for your frontend(s)
* Run the management commang `manage.py migrate_ui`, this will generate the declared components in your frontend, and merge any changes done in safe regions (see next point)
* The generated code contains safe regions enclosed in comments, where custom code can be added. These safe regions will be kept when migrating the UI components again.

## Component Declaration

Example:
```
class OrderTable(ui_migrations.DataTable):
 
	model = models.Order
	max_items_per_page = 4

	fields_options = [
		ui_migrations.DataTable.FieldOptions(
			field_name="id",
			display_name="ID",
			link="/orders/{id}",
			sortable=True,
			auto_generated=True,
		),
		ui_migrations.DataTable.FieldOptions(
			field_name="total_price",
			display_name="Total Price [€]",
			sortable=True,
			modifiable_by_roles=["admin"],
		),
		ui_migrations.DataTable.FieldOptions(
			field_name="date",
			display_name="Date",
			sortable=True,
			modifiable_by_roles=["admin"],
		),
		ui_migrations.DataTable.FieldOptions(
			field_name="status",
			display_name="Status",
			modifiable_by_roles=["admin"],
			custom_components_options=[
				ui_migrations.CustomComponentOptions(
					component_name="StatusWithColor",
					prop_name="status",
				),
			],
		),
		ui_migrations.DataTable.FieldOptions(
			field_name="last_modified",
			display_name="Modified",
		),
	]
	
	actions_options = [
		ui_migrations.ActionOptions(
			display_name="Change Status",
			actions=[
				ui_migrations.IterateAction(field_name="status", direction="forward"),
				ui_migrations.SetCurrentDateAction(field_name="last_modified"),
			],
			roles=["admin", "manager"],
		),
		ui_migrations.ActionOptions(
			display_name="Search Google",
			actions=[
				ui_migrations.OpenUrlAction(url="https://www.google.com/search?q={status}"),
			],
			roles=["admin", "manager", "user"],
		),
	]
```
