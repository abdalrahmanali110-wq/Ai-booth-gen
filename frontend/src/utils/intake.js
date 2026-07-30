const FIELD_ORDER = [
  "brand_name",
  "industry",
  "slogan",
  "event_name",
  "location",
  "event_date",
  "booth_size",
  "open_sides",
  "theme",
  "brand_colors",
  "special_requirements",
  "budget",
];

const OPTIONAL_NULLABLE = new Set(["slogan", "event_date"]);

export function getNextIntakeField(requirements = {}) {
  for (const field of FIELD_ORDER) {
    if (OPTIONAL_NULLABLE.has(field)) {
      if (requirements[field] === null || requirements[field] === undefined) {
        return field;
      }
      continue;
    }
    if (field === "special_requirements") {
      if (requirements.special_requirements === null || requirements.special_requirements === undefined) {
        return field;
      }
      continue;
    }
    if (!requirements[field]) {
      return field;
    }
  }
  return null;
}

const QUICK_REPLIES = {
  industry: [
    "Fashion",
    "Tech",
    "Automotive",
    "Food & Beverage",
    "Jewelry",
    "Government",
    "Finance",
  ],
  slogan: ["Skip", "Innovation for everyone", "Designed to impress"],
  event_name: ["GITEX", "Arab Health", "ADIPEC", "World of Coffee"],
  location: ["Dubai", "Abu Dhabi", "Sharjah", "Riyadh"],
  event_date: ["Skip", "Next month", "Q4 2026"],
  booth_size: ["3x3", "4x4", "6x6", "9x9"],
  open_sides: [
    "1 side",
    "2 sides (corner)",
    "3 sides",
    "All sides",
  ],
  theme: [
    "Premium & Luxury",
    "Modern & Tech",
    "Minimal & Clean",
    "Bold & Playful",
    "Traditional & Elegant",
  ],
  brand_colors: ["Black and gold", "Blue and white", "Red and black", "Green and cream"],
  special_requirements: [
    "Reception desk",
    "LED screens",
    "Meeting room",
    "Seating area",
    "Product shelves",
    "None",
  ],
  budget: [
    "Under 40,000 AED",
    "40,000–90,000 AED",
    "90,000–180,000 AED",
    "180,000+ AED",
  ],
  brand_name: ["Acme", "Nova Motors", "Luxe Beauty", "Gulf Tech"],
};

export function getQuickReplies(requirements = {}) {
  const field = getNextIntakeField(requirements);
  if (!field) return [];
  return (QUICK_REPLIES[field] || []).map((label) => ({ field, label }));
}

export function isBriefReady(requirements = {}) {
  return getNextIntakeField(requirements) === null;
}
