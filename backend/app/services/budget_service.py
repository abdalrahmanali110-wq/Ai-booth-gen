def calculate_budget(suppliers, booth_size):

    supplier_total = sum(
        supplier.get("estimated_cost", 0) or 0
        for supplier in suppliers
    )

    graphics_cost = 5000
    logistics_cost = 3000

    contingency_cost = int(
        supplier_total * 0.10
    )

    size_multiplier = {
        "3x3": 1.0,
        "6x6": 1.3,
        "9x9": 1.7,
        "12x12": 2.2
    }

    multiplier = size_multiplier.get(
        booth_size,
        1.0
    )

    supplier_total = int(
        supplier_total * multiplier
    )
    
    contingency_cost = int(
        supplier_total * 0.10
    )

    grand_total = (
        supplier_total
        + graphics_cost
        + logistics_cost
        + contingency_cost
    )

    return {
        "supplier_costs": supplier_total,
        "graphics_cost": graphics_cost,
        "logistics_cost": logistics_cost,
        "contingency_cost": contingency_cost,
        "grand_total": grand_total
    }