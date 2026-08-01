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

export const STARTER_PROMPTS = [
  "Design a 6x6 fashion booth",
  "Design a corner booth for a tech brand",
  "Design a big open booth with two floors",
  "Design a booth for a car brand",
  "Design a small booth for a food stand",
  "Design a fancy jewelry booth",
  "Design a booth for a government brand",
];

export const FIELD_QUESTIONS = {
  brand_name: "What's your brand name?",
  industry:
    "What industry are you in? Fashion / Tech / Automotive / Food & Beverage / Jewelry / Government / Finance / Other",
  slogan: "What's your slogan or tagline? (optional — say skip if none)",
  event_name: "What's the event name?",
  location: "Where is the event located? (city or venue)",
  event_date:
    "What's the event date? (optional — say skip if you don't know yet)",
  booth_size:
    "What booth size do you need? 3x3 / 4x4 / 6x6 / 9x9 / Custom",
  open_sides:
    "How many open sides? 1 side / 2 sides (corner) / 3 sides / All sides",
  theme:
    "What direction do you want the design to feel? Premium & Luxury / Modern & Tech / Minimal & Clean / Bold & Playful / Traditional & Elegant",
  brand_colors: "What are your brand colors?",
  special_requirements:
    "What do you want inside your booth? Reception desk / LED screens / Meeting room / Seating area / Product shelves / None",
  budget:
    "What's your budget range in AED? Under 40,000 / 40,000–90,000 / 90,000–180,000 / 180,000+",
};

export const FIELD_LABELS = {
  brand_name: "Brand name",
  industry: "Industry",
  slogan: "Slogan",
  event_name: "Event name",
  location: "Location",
  event_date: "Event date",
  booth_size: "Booth size",
  open_sides: "Open sides",
  theme: "Design direction",
  brand_colors: "Brand colors",
  special_requirements: "Inside the booth",
  budget: "Budget",
};

export function getNextIntakeField(requirements = {}) {
  for (const field of FIELD_ORDER) {
    if (OPTIONAL_NULLABLE.has(field)) {
      if (requirements[field] === null || requirements[field] === undefined) {
        return field;
      }
      continue;
    }
    if (field === "special_requirements") {
      if (
        requirements.special_requirements === null ||
        requirements.special_requirements === undefined
      ) {
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
  open_sides: ["1 side", "2 sides (corner)", "3 sides", "All sides"],
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

export function getIntakeQuestion(requirements = {}) {
  const field = getNextIntakeField(requirements);
  if (!field) return null;
  return {
    field,
    ask: FIELD_QUESTIONS[field] || FIELD_LABELS[field] || field,
    options: QUICK_REPLIES[field] || [],
    label: FIELD_LABELS[field] || field,
  };
}

export function isBriefReady(requirements = {}) {
  return getNextIntakeField(requirements) === null;
}

export function formatRequirementValue(key, value) {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) return value.join(", ");
  if (key === "budget" && typeof value === "number") {
    return `${value.toLocaleString()} AED`;
  }
  return String(value);
}

export { FIELD_ORDER };
