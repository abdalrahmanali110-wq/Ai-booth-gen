import requests
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet

def download_image(
        image_url,
        save_path
    ):
        response = requests.get(
        image_url
    )

        with open(
            save_path,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        return save_path


def generate_pdf(
    proposal,
    booth,
    image_url,
    file_path
):

    doc = SimpleDocTemplate(
        file_path
    )

    styles = getSampleStyleSheet()

    content = []

    # Cover Page

    content.append(
        Paragraph(
            proposal["proposal_title"],
            styles["Title"]
        )
    )

    content.append(
        Spacer(1, 20)
    )

    image_path = (
        f"generated_pdfs/images/"
        f"{booth['id']}.jpg"
    )

    download_image(
        image_url,
        image_path
    )

    content.append(
        Image(
            image_path,
            width=400,
            height=300
        )
    )

    content.append(
        Spacer(1, 20)
    )

    content.append(
        Paragraph(
            f"Industry: {booth['industry']}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Theme: {booth['booth_theme']}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Booth Size: {booth['booth_size']}",
            styles["BodyText"]
        )
    )

    content.append(
        PageBreak()
    )

    # Proposal Section

    content.append(
        Paragraph(
            "Project Summary",
            styles["Heading1"]
        )
    )

    content.append(
        Paragraph(
            proposal["proposal_summary"],
            styles["BodyText"]
        )
    )

    doc.build(
        content
    )

    return file_path