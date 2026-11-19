import { useState } from "react";
import { createLead } from "../services/api";
import { getSessionId } from "../hooks/useSession";
import { saveStudentDetails } from "../utils/studentProfile";
import "./ChatLeadForm.css";

interface Props {
  onComplete: () => void;
}

export default function ChatLeadForm({ onComplete }: Props) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanPhone = phone.trim();

    if (!cleanName) {
      setError("Please enter your full name.");
      return;
    }

    if (!/^[6-9]\d{9}$/.test(cleanPhone.replace(/\D/g, ""))) {
      setError("Please enter a valid 10-digit mobile number.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await saveStudentDetails(getSessionId(), { name: cleanName, phone: cleanPhone });
      await createLead({
        name: cleanName,
        phone: cleanPhone,
        program_interest: "Not specified",
        source: "chat_inquiry",
        metadata: { consent_given: true, request_type: "details_shared" },
      });
      onComplete();
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Could not save your details.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="chat-lead-form" aria-label="Share your contact details">
      <div className="chat-lead-form-heading">
        <span className="chat-lead-form-icon" aria-hidden="true">👋</span>
        <div>
          <h2>Let’s get to know you</h2>
          <p>Share your name and mobile number for personalised guidance from SRU Buddy.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <label>
          Your name
          <input
            type="text"
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setError(null);
            }}
            placeholder="Enter your full name"
            autoComplete="name"
            required
          />
        </label>

        <label>
          Mobile number
          <input
            type="tel"
            value={phone}
            onChange={(event) => {
              setPhone(event.target.value);
              setError(null);
            }}
            placeholder="10-digit mobile number"
            inputMode="numeric"
            autoComplete="tel"
            maxLength={15}
            required
          />
        </label>

        {error && <p className="chat-lead-form-error" role="alert">{error}</p>}

        <div className="chat-lead-form-actions">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save details"}
          </button>
          <button type="button" className="chat-lead-form-skip" onClick={onComplete}>
            Skip for now
          </button>
        </div>
      </form>
    </section>
  );
}
