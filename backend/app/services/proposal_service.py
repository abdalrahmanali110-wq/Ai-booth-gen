def generate_proposal(
    booth,
    suppliers,
    budget
):

    summary = f"""
Project Proposal

Industry:
{booth['industry']}

Theme:
{booth['booth_theme']}

Booth Size:
{booth['booth_size']}

Recommended Suppliers:
"""

    for supplier in suppliers:

        summary += f"""

- {supplier['company_name']}
  Estimated Cost:
  {supplier['estimated_cost']} AED
"""

    summary += f"""

Estimated Budget:
{budget['grand_total']} AED

Objective:
Deliver a premium exhibition booth
that maximizes visitor engagement,
brand visibility, and lead generation.
"""

    return summary.strip()