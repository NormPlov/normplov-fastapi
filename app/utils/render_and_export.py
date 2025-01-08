import os
import imgkit
import logging
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.getcwd(), "templates")


def render_assessment_to_image(data: dict, output_path: str):
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        template = env.get_template("assessment_template.html")

        rendered_html = template.render(
            assessment_type=data.get("assessment_type", "Unknown"),
            test_name=data.get("test_name", "Unknown Test"),
            test_uuid=data.get("test_uuid", "N/A"),
            details=data.get("details", [])
        )
        imgkit.from_string(rendered_html, output_path)
    except Exception as e:
        raise

