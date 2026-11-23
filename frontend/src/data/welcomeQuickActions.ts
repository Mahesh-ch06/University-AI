// Quick-action tiles under the opening welcome message, each with a short incentive badge.
// Badges use verified facts only: fee card slabs (up to 40%), NIRF 2025 Engineering rank 91,
// placements page (highest 51 LPA, 150+ recruiters, 1,300+ offers), special concessions on the fee card
// (₹15,000 to ₹50,000 a year). The 4th tile was "How to Apply" until v4.11.0 (still answered when asked).
// The backend keeps the same list (backend/app/services/card_service.py, WELCOME_ACTIONS_CARD).
export const WELCOME_QUICK_ACTIONS = [
  {
    id: "calculate_scholarship",
    icon: "calculator",
    color: "green",
    badge: "Up to 40% off",
    title: "Calculate My Scholarship",
    subtitle: "Instant fee estimate in a few steps",
    prompt: "Calculate my scholarship",
  },
  {
    id: "explore_programs",
    icon: "graduation-cap",
    color: "blue",
    badge: "NIRF #91",
    title: "Explore Programmes",
    subtitle: "B.Tech, MBA, Agriculture & more",
    prompt: "Explore programs offered at SR University",
  },
  {
    id: "placements",
    icon: "briefcase",
    color: "purple",
    badge: "₹51 LPA",
    title: "Placements & Careers",
    subtitle: "150+ recruiters, 1,300+ offers",
    prompt: "Tell me about placements at SRU",
  },
  {
    id: "special_consideration",
    icon: "heart",
    color: "amber",
    badge: "₹15K–₹50K/yr",
    title: "Special Consideration",
    subtitle: "Check concessions you may qualify for",
    prompt: "Special consideration",
  },
];
