from django.core.management.base import BaseCommand
import re

from ...utils import get_components_from_all_apps
from ...ui_frameworks import UiFramework


SAFE_REGION_PATTERN = re.compile(
	r"(\/\* SAFE REGION BEGIN \*\/(.*?)\/\* SAFE REGION END \*\/)|(<!-- SAFE REGION BEGIN -->(.*?)<!-- SAFE REGION END -->)",
	re.DOTALL
)
"""RegEx pattern for matching safe regions"""


class Command(BaseCommand):
	help = 'Migrates the UI components to the frontend.'

	def handle(self, *args, **options) -> None:
		for component, path in get_components_from_all_apps():
			# Generate all components
			component_code = component.generate()
			match component.ui_framework:
				case UiFramework.VUE:
					try:
						with open(f"{path}/src/components/{component.name}.vue", "r") as f:
							old_component_code: str = f.read()
							component_existed = True
					except FileNotFoundError:
						component_existed = False
					with open(f"{path}/src/components/{component.name}.vue", "w") as f:
						if component_existed:
							try:
								# If the same component has been generated before, take the safe regions from the already existing components
								component_code = replace_safe_regions(component_code, old_component_code, SAFE_REGION_PATTERN)
							except ValueError as e:
								if component_existed:
									f.write(old_component_code)
								raise ValueError(f"Failed to merge safe regions in '{component.name}.vue': {e}")
						f.write(component_code)
				case _:
					raise NotImplementedError(f"UI Framework '{component.ui_framework}' is not yet supported.")


def replace_safe_regions(new_component_code: str, old_component_code: str, safe_region_pattern: re.Pattern):
	"""
	Replaces all safe regions in the new component code with the safe regions from the old component code.
	"""
	old_safe_regions = list(match.group() for match in safe_region_pattern.finditer(old_component_code))
	new_safe_region_count = len(list(safe_region_pattern.finditer(new_component_code)))

	if len(old_safe_regions) != new_safe_region_count:
		raise ValueError("The newly generated component has a different number of safe regions than the existing component.")

	old_safe_regions_iter = iter(old_safe_regions)

	return safe_region_pattern.sub(lambda _: next(old_safe_regions_iter), new_component_code)
