import os
import imgkit
import logging
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.getcwd(), "app", "templates")


def render_assessment_to_image(data: dict, output_path: str):
    try:
        logger.info(f"Templates directory: {TEMPLATES_DIR}")
        logger.info(f"Data passed to template: {data}")

        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        template = env.get_template("assessment_template.html")

        rendered_html = template.render(
            assessment_type=data.get("assessment_type", "Unknown"),
            test_name=data.get("test_name", "Unknown Test"),
            test_uuid=data.get("test_uuid", "N/A"),
            details=data.get("details", {})
        )

        logger.info("HTML rendered successfully. Converting to image...")
        imgkit.from_string(rendered_html, output_path)
        logger.info(f"Image saved at: {output_path}")
    except Exception as e:
        logger.error(f"Error in render_assessment_to_image: {e}")
        raise
