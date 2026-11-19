import { useState, useEffect, useRef } from "react";
import { createLead } from "../services/api";
import { getSessionId } from "../hooks/useSession";
import { readStudentDetails, saveStudentDetails, cleanPhone } from "../utils/studentProfile";
import { UserIcon, PhoneIcon } from "./Icons";
import "./ChatLeadForm.css";

interface Props {
  onComplete: () => void;
}

export default function ChatLeadForm({ onComplete }: Props) {
  const existing = readStudentDetails();
  const initialName = existing?.name?.trim() || "";
  const initialHasName = Boolean(initialName.length >= 2);

  const [step, setStep] = useState<1 | 2>(initialHasName ? 2 : 1);
  const [name, setName] = useState(initialName);
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nameInputRef = useRef<HTMLInputElement>(null);
  const phoneInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (step === 1) {
      nameInputRef.current?.focus();
    } else {
      phoneInputRef.current?.focus();
    }
  }, [step]);

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = name.trim();
    if (!clean || clean.length < 2) {
      setError("Please enter your name.");
      return;
    }
    setError(null);
    setStep(2);
  };

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanN = name.trim();
    const rawP = phone.trim();
    const validPhone = cleanPhone(rawP);

    if (!cleanN || cleanN.length < 2) {
      setStep(1);
      setError("Please enter your name first.");
      return;
    }

    if (!validPhone) {
      setError("Please enter a valid 10-digit mobile number.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await saveStudentDetails(getSessionId(), { name: cleanN, phone: validPhone });
      const activeConv = sessionStorage.getItem("sru_active_conv_id");
      await createLead({
        name: cleanN,
        phone: validPhone,
        program_interest: "Not specified",
        source: "chat_inquiry",
        conversation_id: activeConv || undefined,
        metadata: { consent_given: true, request_type: "conversational_lead" },
      });
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save details. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="chat-lead-form card-animate" aria-label="Student details">
      {step === 1 ? (
        <form onSubmit={handleStep1Submit} className="chat-lead-step">
          <div className="chat-lead-form-heading">
            <span className="chat-lead-form-icon" aria-hidden="true">
              <UserIcon size={20} color="#0055a4" />
            </span>
            <div>
              <h2>How can I call you?</h2>
              <p>Please share your name to personalize your conversation with SRU Buddy.</p>
            </div>
          </div>

          <label>
            Your Name
            <input
              ref={nameInputRef}
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError(null);
              }}
              placeholder="Enter your name"
              autoComplete="name"
              required
            />
          </label>

          {error && <p className="chat-lead-form-error" role="alert">{error}</p>}

          <div className="chat-lead-form-actions">
            <button type="submit" className="chat-lead-submit-btn">
              Continue →
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleStep2Submit} className="chat-lead-step">
          <div className="chat-lead-form-heading">
            <span className="chat-lead-form-icon" aria-hidden="true">
              <PhoneIcon size={20} color="#0055a4" />
            </span>
            <div>
              <h2>Nice to meet you, {name}!</h2>
              <p className="chat-lead-tagline">
                If chat is disconnected, we will connect you again.
              </p>
            </div>
          </div>

          <label>
            Mobile Number
            <input
              ref={phoneInputRef}
              type="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
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
            <button type="submit" className="chat-lead-submit-btn" disabled={isSubmitting}>
              {isSubmitting ? "Connecting..." : "Get Answer →"}
            </button>
            <button
              type="button"
              className="chat-lead-back-btn"
              onClick={() => {
                setError(null);
                setStep(1);
              }}
            >
              ← Edit name
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
