
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
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently';
  }
}

export default function RecoveryCard({
  context,
  onContinue,
  onStartFresh,
  isContinuing = false,
}: Props) {
  const name = context.student_name?.trim();
  const titleGreeting = name ? `Welcome back, ${name}!` : 'Welcome back!';
  const message = context.welcome_message || 'I found your previous conversation. Would you like to continue where you left off or start fresh?';
  const relativeTime = formatRelativeTime(context.last_active_at);

  const isCompleted = context.assessment_status === 'completed';
  const isInProgress = context.assessment_status === 'in_progress';
  const hasScholarship = typeof context.scholarship_percent === 'number' && context.scholarship_percent > 0;

  return (
    <div className="sru-recovery-card" role="region" aria-label="Previous conversation recovery">
      {/* Decorative gradient aura */}
      <div className="sru-recovery-aura" />

      <div className="sru-recovery-inner">
        {/* Top Header */}
        <div className="sru-recovery-header">
          <div className="sru-recovery-icon-wrap">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
          </div>
          <div className="sru-recovery-header-text">
            <div className="sru-recovery-greeting-row">
              <h3 className="sru-recovery-title">{titleGreeting}</h3>
              <span className="sru-recovery-time-badge" title="Last active time">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                {relativeTime}
              </span>
            </div>
            <p className="sru-recovery-desc">{message}</p>
          </div>
        </div>

        {/* Previous Conversation Summary Box */}
        <div className="sru-recovery-summary-box">
          {context.topic && (
            <div className="sru-recovery-topic-row">
              <span className="sru-recovery-topic-tag">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                  <path d="M6 12v5c3 3 9 3 12 0v-5" />
                </svg>
                {context.topic}
              </span>
              {hasScholarship && (
                <span className="sru-recovery-scholarship-pill">
                  🏆 {context.scholarship_percent}% Fee Waiver
                </span>
              )}
            </div>
          )}

          <div className="sru-recovery-grid">
            {context.program_name && (
              <div className="sru-recovery-fact">
                <span className="sru-recovery-fact-label">Programme</span>
                <span className="sru-recovery-fact-val" title={context.program_name}>
                  {context.program_name}
                </span>
              </div>
            )}

            {(context.board_name || context.academic_stage) && (
              <div className="sru-recovery-fact">
                <span className="sru-recovery-fact-label">Board / Stage</span>
                <span className="sru-recovery-fact-val">
                  {[context.board_name, context.academic_stage].filter(Boolean).join(' • ')}
                  {context.is_projected && ' (Projected)'}
                </span>
              </div>
            )}

            {context.score_text && (
              <div className="sru-recovery-fact">
                <span className="sru-recovery-fact-label">Marks / Score</span>
                <span className="sru-recovery-fact-val">{context.score_text}</span>
              </div>
            )}

            {context.scholarship_label && (
              <div className="sru-recovery-fact">
                <span className="sru-recovery-fact-label">Status / Result</span>
                <span className={`sru-recovery-fact-val ${isCompleted ? 'sru-val-success' : isInProgress ? 'sru-val-progress' : ''}`}>
                  {context.scholarship_label}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="sru-recovery-actions">
          <button
            type="button"
            className="sru-recovery-btn sru-recovery-btn-continue"
            onClick={onContinue}
            disabled={isContinuing}
          >
            {isContinuing ? (
              <>
                <span className="sru-spinner-small" />
                <span>Restoring...</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>Continue Previous Conversation</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="sru-recovery-btn sru-recovery-btn-fresh"
            onClick={onStartFresh}
            disabled={isContinuing}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Start Fresh</span>
          </button>
        </div>
      </div>
    </div>
  );
}
