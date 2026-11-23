// Unit tests for isEligibleResponse gating of confetti falling effect
import assert from "node:assert";

// Mock version of isEligibleResponse logic matching frontend/src/utils/effects.ts
function isEligibleResponse(data) {
  if (data.eligible === true) return true;
  if (data.eligible === false) return false;

  const text = (data.answer || "").toLowerCase();
  if (!text) return false;

  const ineligiblePhrases = [
    "not eligible",
    "not be eligible",
    "ineligible",
    "below 50%",
    "below the 50%",
    "does not meet",
    "do not meet",
    "cannot be provided",
    "sorry, but with",
    "sorry you are not",
    "unfortunately",
  ];
  if (ineligiblePhrases.some((phrase) => text.includes(phrase))) {
    return false;
  }

  const eligiblePhrases = [
    "eligible for admission",
    "eligible for our",
    "eligible to apply",
    "qualify for our",
    "qualify for an",
    "qualify for a",
    "qualify for merit",
    "qualify for the",
    "qualifies you for",
    "qualifies for",
    "fully eligible",
    "congratulations on qualifying",
    "you are eligible",
    "you're eligible",
    "top-tier merit scholarship",
    "premier merit scholarship",
    "highest merit scholarship",
    "merit scholarship tier",
    "tuition fee waiver",
    "scholarship reduction",
    "### your scholarship assessment",
    "matching scholarship category",
    "meets the academic eligibility",
    "meet the academic eligibility",
    "meets the eligibility",
    "meet the eligibility",
    "fulfill sr university's academic eligibility",
    "fulfills sr university's academic eligibility",
  ];

  if (eligiblePhrases.some((phrase) => text.includes(phrase))) {
    return true;
  }

  if (data.cards && Array.isArray(data.cards)) {
    const hasFeeCalc = data.cards.some((c) => c?.type === "calculate_fee" && c?.data?.status === "ok");
    if (hasFeeCalc) {
      return true;
    }
  }

  return false;
}

// Test cases
const tests = [
  // Ineligible tests (MUST BE FALSE)
  {
    name: "Below 50% percentage rejection",
    data: { answer: "Sorry, but with 45%, you are not eligible for admission to undergraduate programmes at SR University (minimum 50% required). Consequently, fee details cannot be provided." },
    expected: false,
  },
  {
    name: "Below 500 raw marks rejection",
    data: { answer: "Sorry, but with 450/1000 (45.0%), you are not eligible for admission. Minimum 50% is required." },
    expected: false,
  },
  {
    name: "Explicit eligible: false flag",
    data: { eligible: false, answer: "You might check other pathways" },
    expected: false,
  },
  {
    name: "Generic greeting message",
    data: { answer: "Hello! Welcome to SR University. How can I help you today?" },
    expected: false,
  },
  {
    name: "Hostel fee general inquiry",
    data: { answer: "SR University offers AC and Non-AC hostel accommodations starting from ₹95,000/year." },
    expected: false,
  },

  // Eligible tests (MUST BE TRUE)
  {
    name: "Explicit eligible: true flag",
    data: { eligible: true, answer: "Welcome to SR University!" },
    expected: true,
  },
  {
    name: "Outstanding 94% merit variant",
    data: { answer: "🌟 Outstanding academic performance! With 94% in your qualifying examinations, you are eligible for admission with our top-tier merit scholarship! Let me prepare your detailed fee and scholarship structure." },
    expected: true,
  },
  {
    name: "Excellent 85% merit variant",
    data: { answer: "🎉 Excellent result! With 85%, you qualify for merit scholarship benefits at SR University. Here is the complete breakdown." },
    expected: true,
  },
  {
    name: "Good 72% merit variant",
    data: { answer: "👏 Good effort! With 72%, you are eligible for admission to SR University and qualify for merit scholarship privileges." },
    expected: true,
  },
  {
    name: "Standard 58% eligible variant",
    data: { answer: "✅ You are eligible for admission! With 58%, you meet the eligibility criteria for our degree programmes." },
    expected: true,
  },
  {
    name: "Scholarship assessment block",
    data: { answer: "### Your Scholarship Assessment\n\nProgramme: B.Tech CSE\nTuition Fee: ₹1,50,000" },
    expected: true,
  },
  {
    name: "Calculate fee card present",
    data: { answer: "Here is your calculation:", cards: [{ type: "calculate_fee", data: { status: "ok", net_fee: 105000 } }] },
    expected: true,
  },
];

let passed = 0;
for (const t of tests) {
  const result = isEligibleResponse(t.data);
  assert.strictEqual(
    result,
    t.expected,
    `Failed '${t.name}': expected ${t.expected}, got ${result} (input answer: "${t.data.answer || ""}")`
  );
  passed++;
}

console.log(`isEligibleResponse: all ${passed} tests passed successfully.`);
