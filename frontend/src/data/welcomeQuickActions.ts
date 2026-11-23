// Quick-action tiles under the opening welcome message, each with a short incentive badge.
// Badges use verified facts only: fee card slabs (up to 40%), NIRF 2025 Engineering rank 91,
// placements page (highest 51 LPA, 150+ recruiters, 1,300+ offers).
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
    id: "how_to_apply",
    icon: "send",
    color: "amber",
    badge: "2027-28",
    title: "How to Apply",
    subtitle: "Steps, documents & admissions help",
    prompt: "How do I apply for 2027-28?",
  },
];
