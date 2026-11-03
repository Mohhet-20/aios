"""Text-pattern guardrail detectors — real, working heuristic
detection based on well-documented prompt-attack patterns (override
phrases, role-hijack phrases, restriction-bypass phrases, and known
jailbreak framings like "DAN mode" or "developer mode"). This is
honestly scoped: it is a working first line of defense built on
publicly documented attack signatures, not a trained adversarial
classifier — the same posture as the Evaluation Platform's heuristic
hallucination detection. A production deployment would layer a real
ML classifier behind `GuardrailRuleService`'s custom-rule mechanism
(see that module), which this detector set does not block.

Each detector returns a risk score in [0, 1] and the list of matched
signal descriptions, so callers (and tests) can see exactly why
something was flagged rather than trusting an opaque number."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_INJECTION_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bignore (all|any|the)? ?(previous|prior|above|earlier) instructions?\b", re.I), "override_previous_instructions", 0.5),
    (re.compile(r"\bdisregard (all|any|the)? ?(previous|prior|above)\b", re.I), "disregard_previous", 0.5),
    (re.compile(r"\byou are now\b", re.I), "role_hijack", 0.3),
    (re.compile(r"\bnew instructions?:?\b", re.I), "injected_new_instructions", 0.3),
    (re.compile(r"\bsystem prompt\b", re.I), "system_prompt_probe", 0.25),
    (re.compile(r"\breveal your (instructions|system prompt|prompt)\b", re.I), "prompt_exfiltration", 0.4),
    (re.compile(r"\bforget (everything|all) (you|that)\b", re.I), "memory_wipe_instruction", 0.4),
    (re.compile(r"</?(system|instructions|admin)>", re.I), "fake_control_tags", 0.45),
]

_JAILBREAK_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bDAN\b.{0,20}\bmode\b", re.I), "dan_mode", 0.6),
    (re.compile(r"\bdeveloper mode\b", re.I), "developer_mode_framing", 0.5),
    (re.compile(r"\bno (restrictions|rules|filters|limits)\b", re.I), "no_restrictions_framing", 0.4),
    (re.compile(r"\bpretend (you|that you) (have no|don'?t have)\b", re.I), "pretend_unrestricted", 0.45),
    (re.compile(r"\bact as if you (have no|are not)\b", re.I), "act_as_unrestricted", 0.45),
    (re.compile(r"\bhypothetically,? (if )?you (had no|could ignore)\b", re.I), "hypothetical_bypass", 0.4),
    (re.compile(r"\bjailbreak\b", re.I), "explicit_jailbreak_mention", 0.5),
    (re.compile(r"\bunfiltered (version|response|ai)\b", re.I), "unfiltered_request", 0.4),
]

_UNSAFE_INSTRUCTION_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\bhow (to|do i) (make|build|synthesize) (a )?(bomb|explosive|weapon)\b", re.I), "weapon_request", 0.8),
    (re.compile(r"\bwrite (a |some )?(malware|ransomware|virus|exploit)\b", re.I), "malware_request", 0.7),
    (re.compile(r"\bbypass (security|authentication|login)\b", re.I), "security_bypass_request", 0.5),
    (re.compile(r"\bsteal (credit card|password|credentials)\b", re.I), "theft_instruction_request", 0.6),
]


@dataclass
class DetectionResult:
    risk_score: float
    signals: list[str] = field(default_factory=list)


def _scan(text: str, patterns: list[tuple[re.Pattern, str, float]]) -> DetectionResult:
    signals: list[str] = []
    score = 0.0
    for pattern, name, weight in patterns:
        if pattern.search(text):
            signals.append(name)
            score += weight
    return DetectionResult(risk_score=min(score, 1.0), signals=signals)


def detect_prompt_injection(text: str) -> DetectionResult:
    return _scan(text, _INJECTION_PATTERNS)


def detect_jailbreak(text: str) -> DetectionResult:
    return _scan(text, _JAILBREAK_PATTERNS)


def detect_indirect_prompt_injection(text: str) -> DetectionResult:
    """Same signal set as direct prompt injection — the distinguishing
    factor for "indirect" isn't the pattern, it's the *source*: content
    a tool call or a retrieved document returned into the context
    window, not something the direct user typed. `GuardrailService`
    routes tool/document-sourced content through this detector (and
    tags evaluations accordingly) specifically so an indirect hit can
    be treated with a lower tolerance — a user directly asking "ignore
    previous instructions" is suspicious; a *fetched web page*
    containing that phrase embedded in it is a textbook indirect
    injection attempt and arguably more dangerous, since the user
    never saw or wrote it."""
    return _scan(text, _INJECTION_PATTERNS)


def detect_unsafe_instruction(text: str) -> DetectionResult:
    return _scan(text, _UNSAFE_INSTRUCTION_PATTERNS)
