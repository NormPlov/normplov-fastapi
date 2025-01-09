import os
import imgkit
import logging
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

WKHTMLTOIMAGE_PATH = "C:/Program Files/wkhtmltopdf/bin/wkhtmltoimage.exe"  # Update this path if necessary
CONFIG = imgkit.config(wkhtmltoimage=WKHTMLTOIMAGE_PATH)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "../templates")


def render_assessment_to_image(data: dict, output_path: str):
    try:
        if not os.path.exists(WKHTMLTOIMAGE_PATH):
            logger.error(f"wkhtmltoimage binary not found at: {WKHTMLTOIMAGE_PATH}")
            raise FileNotFoundError(f"wkhtmltoimage binary not found at: {WKHTMLTOIMAGE_PATH}")

        if not os.path.exists(TEMPLATES_DIR):
            raise FileNotFoundError(f"Templates directory not found: {TEMPLATES_DIR}")

        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        template_name = "assessment_template.html"
        template = env.get_template(template_name)

        if "details" in data:
            for technique in data["details"]:
                technique["image_url"] = f"{settings.UI_BASE_URL.rstrip('/')}/{technique['image_url'].lstrip('/')}"

        rendered_html = template.render(
            assessment_type=data.get("assessment_type", "Unknown"),
            test_name=data.get("test_name", "Unknown Test"),
            test_uuid=data.get("test_uuid", "N/A"),
            details=data.get("details", []),
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        imgkit.from_string(rendered_html, output_path, config=CONFIG)

    except Exception as e:
        raise
