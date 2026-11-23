import type { ConversationRecoveryContext } from '../services/api';
import './RecoveryCard.css';

interface Props {
  context: ConversationRecoveryContext;
  onContinue: () => void;
  onStartFresh: () => void;
  isContinuing?: boolean;
}

function formatRelativeTime(dateStr?: string | null): string {
  if (!dateStr) return 'Recently';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs < 0) return 'Just now';
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently';
  }
}

function formatName(name?: string | null): string {
  if (!name) return '';
  const clean = name.trim().replace(/^,+|,+$/g, '').trim();
  if (!clean) return '';
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

function formatLabel(val?: string | null): string {
  if (!val) return '';
  const map: Record<string, string> = {
    btech_cse: 'B.Tech CSE',
    btech_ai_ds: 'B.Tech AI & Data Science',
    btech_ece: 'B.Tech ECE',
    btech_eee: 'B.Tech EEE',
    btech_mech: 'B.Tech Mechanical',
    btech_civil: 'B.Tech Civil',
    state_board: 'State Board',
    ts_state_board: 'TS State Board',
    bieap: 'AP Board (BIEAP)',
    cbse: 'CBSE',
    icse: 'ICSE',
    inter_1st: 'Inter 1st Year',
    inter_2nd: 'Inter 2nd Year',
    completed: '12th Completed',
  };
  const key = val.toLowerCase().trim();
  if (map[key]) return map[key];
  return val.replace(/_/g, ' ').replace(/\w/g, (c) => c.toUpperCase());
}

export default function RecoveryCard({
  context,
  onContinue,
  onStartFresh,
  isContinuing = false,
}: Props) {
  const formattedName = formatName(context.student_name);
  const titleGreeting = formattedName ? `Welcome back, ${formattedName}!` : 'Welcome back!';
  const relativeTime = formatRelativeTime(context.last_active_at);

  const progLabel = formatLabel(context.program_name);
  const boardLabel = formatLabel(context.board_name);
  const stageLabel = formatLabel(context.academic_stage);
  const hasScholarship = typeof context.scholarship_percent === 'number' && context.scholarship_percent > 0;
  const isCompleted = context.assessment_status === 'completed';
  const isInProgress = context.assessment_status === 'in_progress';

  let shortNote = 'Pick up where you left off or start fresh.';
  if (isCompleted) {
    if (hasScholarship) {
      shortNote = `Eligible for a ${context.scholarship_percent}% tuition fee waiver.`;
    } else {
      shortNote = 'Your assessment details are saved. Admissions are open.';
    }
  } else if (isInProgress) {
    shortNote = 'Your academic details are saved. Ready to continue?';
  }

  return (
    <div className="sru-rec-card-mini" role="region" aria-label="Conversation recovery">
      <div className="sru-rec-aura-line" />

      {/* Header Row */}
      <div className="sru-rec-top">
        <div className="sru-rec-title-group">
          <span className="sru-rec-icon" aria-hidden="true">✨</span>
          <span className="sru-rec-heading">{titleGreeting}</span>
        </div>
        <span className="sru-rec-time-chip">{relativeTime}</span>
      </div>

      {/* Structured Academic Details Grid */}
      <div className="sru-rec-details-grid">
        {progLabel && (
          <div className="sru-rec-detail-item">
            <span className="sru-rec-detail-label">🎓 Programme</span>
            <span className="sru-rec-detail-val" title={progLabel}>{progLabel}</span>
          </div>
        )}
        {(boardLabel || stageLabel) && (
          <div className="sru-rec-detail-item">
            <span className="sru-rec-detail-label">📚 Board / Stage</span>
            <span className="sru-rec-detail-val">
              {[boardLabel, stageLabel].filter(Boolean).join(' • ')}
            </span>
          </div>
        )}
        {context.score_text && (
          <div className="sru-rec-detail-item">
            <span className="sru-rec-detail-label">📊 Academic Marks</span>
            <span className="sru-rec-detail-val">{context.score_text}</span>
          </div>
        )}
        <div className="sru-rec-detail-item">
          <span className="sru-rec-detail-label">🏆 Admission Status</span>
          <span className="sru-rec-detail-val sru-rec-highlight">
            {hasScholarship
              ? `${context.scholarship_percent}% Fee Waiver`
              : isCompleted
              ? 'Admissions Open'
              : isInProgress
              ? 'In Progress'
              : 'Saved Profile'}
          </span>
        </div>
      </div>

      {/* Short Note */}
      <p className="sru-rec-note">{shortNote}</p>

      {/* Prominent Action Buttons Side-by-Side */}
      <div className="sru-rec-btn-row">
        <button
          type="button"
          className="sru-rec-btn-action sru-rec-btn-primary"
          onClick={onContinue}
          disabled={isContinuing}
          aria-label="Continue previous conversation"
        >
          {isContinuing ? (
            <>
              <span className="sru-spinner-mini" />
              <span>Restoring...</span>
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="6 4 20 12 6 20 6 4" />
              </svg>
              <span>Continue Previous Chat</span>
            </>
          )}
        </button>

        <button
          type="button"
          className="sru-rec-btn-action sru-rec-btn-secondary"
          onClick={onStartFresh}
          disabled={isContinuing}
          aria-label="Start fresh conversation"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
          </svg>
          <span>Start Fresh</span>
        </button>
      </div>
    </div>
  );
}
