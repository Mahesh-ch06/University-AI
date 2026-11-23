// Checks for the eligibility confetti (src/utils/effects.ts).
//   npm run test:effects
// 1. Only the server's explicit `eligible: true` flag counts. Reply text is never read, so
//    hostel, fee-structure and general answers that mention "scholarship" or "waiver" never trigger it.
// 2. The celebration plays once per chat session.
import assert from "node:assert/strict";
import { claimEligibilityCelebration, isEligibleResponse } from "../src/utils/effects.ts";

let passed = 0;
const check = (actual, expected, label) => {
  assert.strictEqual(actual, expected, label);
  passed++;
};

const notEligible = [
  ["Below 50% rejection", { eligible: false, answer: "Sorry, but with 45%, you are not eligible for admission." }],
  ["Greeting", { answer: "Hello! Welcome to SR University. How can I help you today?" }],
  ["Hostel answer", { answer: "Hostel fees: ₹1,15,000 to ₹1,35,000 a year.", cards: [{ type: "fee_breakdown" }] }],
  ["Fee structure mentioning waivers", { answer: "Merit scholarships give a 10% to 40% tuition fee waiver." }],
  ["Eligible-sounding text without the flag", { answer: "You are eligible for admission with a merit scholarship!" }],
  ["Plain fee card without the flag", { answer: "B.Tech CSE fee", cards: [{ type: "calculate_fee", data: { status: "ok" } }] }],
];
for (const [label, data] of notEligible) check(isEligibleResponse(data), false, label);

check(isEligibleResponse({ eligible: true, answer: "Your Scholarship Assessment" }), true, "Server flag eligible: true");

check(claimEligibilityCelebration("session-a"), true, "First eligible result in a session celebrates");
check(claimEligibilityCelebration("session-a"), false, "Second eligible result in the same session does not");
check(claimEligibilityCelebration("session-a"), false, "Nor any later one");
check(claimEligibilityCelebration("session-b"), true, "A new chat session can celebrate once");

console.log(`effects: all ${passed} checks passed.`);
