"""
SENTINEL 1.5 - ZAI Shell Self-Preservation System

Sentinel exists to prevent ZAI Shell from making a broken system worse.

This is not a feature. This is ZAI Shell's sense of self-preservation.

SENTINEL 1.5 EVOLUTION:
- 1.0 watched. 1.5 understands.
- 1.0 said "high risk". 1.5 says "high risk BECAUSE..."
- 1.0 gave numbers. 1.5 tells stories.
- 1.0 observed events. 1.5 recognizes patterns.

SENTINEL 1.5 PHILOSOPHY:
- Sentinel OBSERVES, it does not COMMAND
- Sentinel EXPLAINS, it does not JUDGE
- Sentinel REMEMBERS LESSONS, not everything
- Sentinel speaks to SURVIVE, not to CONTROL
- Silence is also a signal

THE SENTINEL OATH:
Sentinel exists to prevent ZAI Shell from making a broken system worse.
If Sentinel's warnings unnecessarily slow system progress, Sentinel is also at fault.
The human always has final say.
"""

import time
import json
import datetime
import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from pathlib import Path


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class IntentCategory(Enum):
    READ_ONLY = "read_only"
    MODIFICATION = "modification"
    DELETION = "deletion"
    SYSTEM_CHANGE = "system_change"
    NETWORK_ACCESS = "network_access"
    INSTALLATION = "installation"
    REPAIR = "repair"
    UNKNOWN = "unknown"


@dataclass
class RiskBreakdown:
    """
    SENTINEL 1.5: Risk is not a number, it's a story.
    
    Four dimensions of risk:
    - Structural: What is being targeted? (path, irreversibility)
    - Behavioral: What pattern is emerging? (loops, escalation)
    - Contextual: What is the current state? (degraded, panicking)
    - Intent: What is the purpose? (deletion, system change)
    """
    structural_score: int = 0
    structural_reasons: List[str] = field(default_factory=list)
    
    behavioral_score: int = 0
    behavioral_reasons: List[str] = field(default_factory=list)
    
    contextual_score: int = 0
    contextual_reasons: List[str] = field(default_factory=list)
    
    intent_score: int = 0
    intent_reasons: List[str] = field(default_factory=list)
    
    @property
    def total_score(self) -> int:
        return min(100, self.structural_score + self.behavioral_score + 
                   self.contextual_score + self.intent_score)
    
    @property
    def all_reasons(self) -> List[str]:
        reasons = []
        if self.structural_reasons:
            reasons.extend(self.structural_reasons)
        if self.behavioral_reasons:
            reasons.extend(self.behavioral_reasons)
        if self.contextual_reasons:
            reasons.extend(self.contextual_reasons)
        if self.intent_reasons:
            reasons.extend(self.intent_reasons)
        return reasons
    
    @property
    def is_accumulated(self) -> bool:
        """Check if risk is accumulated (not sudden)"""
        non_zero_dimensions = sum([
            1 if self.behavioral_score > 0 else 0,
            1 if self.contextual_score > 0 else 0,
        ])
        return non_zero_dimensions >= 1 and (self.behavioral_score + self.contextual_score) > 20
    
    def get_narrative(self) -> str:
        """Generate a human-readable risk narrative"""
        if self.total_score < 20:
            return ""
        
        parts = []
        
        if self.is_accumulated:
            parts.append("Risk is accumulated, not sudden.")
        
        if self.structural_reasons:
            parts.append(f"Structural: {'; '.join(self.structural_reasons)}")
        
        if self.behavioral_reasons:
            parts.append(f"Behavioral: {'; '.join(self.behavioral_reasons)}")
        
        if self.contextual_reasons:
            parts.append(f"Contextual: {'; '.join(self.contextual_reasons)}")
        
        if self.intent_reasons:
            parts.append(f"Intent: {'; '.join(self.intent_reasons)}")
        
        return " | ".join(parts) if parts else ""


@dataclass
class Lesson:
    """
    SENTINEL 1.5: Memory exists not to punish, but to prevent repetition.
    
    A lesson is learned from a past mistake that caused actual damage.
    Sentinel doesn't remember everything - only what matters.
    """
    timestamp: float
    pattern_type: str
    trigger: str
    consequence: str
    times_seen: int = 1
    last_seen: float = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "pattern_type": self.pattern_type,
            "trigger": self.trigger,
            "consequence": self.consequence,
            "times_seen": self.times_seen,
            "last_seen": self.last_seen or self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Lesson':
        return cls(
            timestamp=data.get("timestamp", time.time()),
            pattern_type=data.get("pattern_type", "unknown"),
            trigger=data.get("trigger", ""),
            consequence=data.get("consequence", ""),
            times_seen=data.get("times_seen", 1),
            last_seen=data.get("last_seen", data.get("timestamp", time.time()))
        )


@dataclass
class BehaviorSignal:
    """A single behavioral signal that Sentinel observes"""
    timestamp: float
    intent_category: IntentCategory
    action_type: str
    description: str
    target: str
    success: bool
    error_message: Optional[str] = None
    risk_breakdown: Optional[RiskBreakdown] = None
    retry_attempt: int = 0
    previous_failures: int = 0
    is_panic_mode: bool = False


@dataclass
class SentinelState:
    """Current state of the Sentinel system"""
    consecutive_failures: int = 0
    repair_attempt_count: int = 0
    risk_escalation_trend: List[int] = field(default_factory=list)
    last_successful_action_time: float = 0
    system_damage_indicators: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    is_degraded: bool = False
    is_panic_mode: bool = False
    panic_indicators: List[str] = field(default_factory=list)
    warnings_given_this_session: int = 0


class SentinelVerdict:
    """
    SENTINEL 1.5 Verdict
    
    Key changes from 1.0:
    - Explains WHY, not just WHAT
    - Provides risk breakdown (structural, behavioral, contextual, intent)
    - Tells if risk is accumulated vs sudden
    - Never judges, only informs
    """
    
    def __init__(
        self,
        threat_level: ThreatLevel,
        reason: str,
        risk_breakdown: Optional[RiskBreakdown] = None,
        recommendation: Optional[str] = None,
        sentinel_recommends_stop: bool = False,
        lessons_applied: Optional[List[Lesson]] = None
    ):
        self.allow = True
        self.threat_level = threat_level
        self.reason = reason
        self.risk_breakdown = risk_breakdown or RiskBreakdown()
        self.recommendation = recommendation
        self.sentinel_recommends_stop = sentinel_recommends_stop
        self.lessons_applied = lessons_applied or []
        self.timestamp = time.time()
    
    @property
    def warning_level(self) -> str:
        return self.threat_level.name
    
    @property
    def is_dangerous(self) -> bool:
        return self.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
    
    @property
    def should_warn_user(self) -> bool:
        """Only warn for MODERATE and above. Silence is also a signal."""
        return self.threat_level in [ThreatLevel.MODERATE, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
    
    @property
    def full_explanation(self) -> str:
        """
        SENTINEL 1.5: Danger is not hidden, it is decomposed.
        Returns full explanation with all reasons.
        """
        parts = [f"Risk Level: {self.threat_level.name}"]
        
        if self.risk_breakdown and self.risk_breakdown.all_reasons:
            parts.append("Because:")
            for reason in self.risk_breakdown.all_reasons:
                parts.append(f"  • {reason}")
        
        if self.risk_breakdown and self.risk_breakdown.is_accumulated:
            parts.append("⚠️ This risk is not sudden, it is accumulated.")
        
        if self.lessons_applied:
            parts.append("Past Lessons:")
            for lesson in self.lessons_applied:
                parts.append(f"  📚 {lesson.trigger} → {lesson.consequence} (seen {lesson.times_seen}x)")
        
        if self.recommendation:
            parts.append(f"→ {self.recommendation}")
        
        return "\n".join(parts)
    
    def __str__(self):
        if self.sentinel_recommends_stop:
            return f"[SENTINEL WARNING] {self.threat_level.name}: {self.reason}"
        return f"[SENTINEL] {self.threat_level.name}: {self.reason}"


class LessonMemory:
    """
    SENTINEL 1.5: Lightweight Lesson Memory
    
    Sentinel doesn't remember everything.
    Sentinel remembers the same mistakes.
    
    Types of lessons:
    - path_damage: "This path caused system damage before"
    - repair_failure: "This type of repair crashed twice"
    - escalation_pattern: "This escalation pattern usually fails"
    - panic_damage: "Actions in panic mode caused damage"
    """
    
    LESSON_FILE = ".sentinel_lessons.json"
    MAX_LESSONS = 50
    
    def __init__(self):
        self.lessons: List[Lesson] = []
        self._load_lessons()
    
    def _load_lessons(self):
        try:
            if os.path.exists(self.LESSON_FILE):
                with open(self.LESSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.lessons = [Lesson.from_dict(l) for l in data.get("lessons", [])]
        except Exception:
            self.lessons = []
    
    def _save_lessons(self):
        try:
            data = {"lessons": [l.to_dict() for l in self.lessons]}
            with open(self.LESSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def learn(self, pattern_type: str, trigger: str, consequence: str):
        """
        Learn a new lesson or reinforce an existing one.
        
        Principle: Past exists not to punish, but to prevent repetition.
        """
        trigger_lower = trigger.lower()
        
        for lesson in self.lessons:
            if lesson.pattern_type == pattern_type and lesson.trigger.lower() == trigger_lower:
                lesson.times_seen += 1
                lesson.last_seen = time.time()
                self._save_lessons()
                return
        
        new_lesson = Lesson(
            timestamp=time.time(),
            pattern_type=pattern_type,
            trigger=trigger,
            consequence=consequence,
            times_seen=1,
            last_seen=time.time()
        )
        self.lessons.append(new_lesson)
        
        if len(self.lessons) > self.MAX_LESSONS:
            self.lessons.sort(key=lambda x: (x.times_seen, x.last_seen), reverse=True)
            self.lessons = self.lessons[:self.MAX_LESSONS]
        
        self._save_lessons()
    
    def recall(self, pattern_type: Optional[str] = None, trigger_contains: Optional[str] = None) -> List[Lesson]:
        """Recall relevant lessons"""
        results = []
        
        for lesson in self.lessons:
            if pattern_type and lesson.pattern_type != pattern_type:
                continue
            if trigger_contains and trigger_contains.lower() not in lesson.trigger.lower():
                continue
            results.append(lesson)
        
        return sorted(results, key=lambda x: x.times_seen, reverse=True)
    
    def has_lesson_for_path(self, path: str) -> Optional[Lesson]:
        """Check if there's a lesson about this path"""
        path_lower = path.lower()
        for lesson in self.lessons:
            if lesson.pattern_type == "path_damage" and lesson.trigger.lower() in path_lower:
                return lesson
        return None
    
    def has_lesson_for_pattern(self, pattern: str) -> Optional[Lesson]:
        """Check if there's a lesson about this pattern"""
        pattern_lower = pattern.lower()
        for lesson in self.lessons:
            if pattern_lower in lesson.trigger.lower():
                return lesson
        return None
    
    def clear(self):
        """Clear all lessons (requires explicit user action)"""
        self.lessons = []
        self._save_lessons()


class Sentinel:
    """
    SENTINEL 1.5 - ZAI Shell Self-Preservation System
    
    Evolution from 1.0:
    - 1.0 watched. 1.5 understands.
    - Risk is now a story, not a number
    - Lessons are remembered, not everything
    - Explains WHY, never judges
    - Silence is a deliberate signal
    
    Core Question: "Is this system still survivable after this action?"
    
    Protection Priority (in order):
    1. System integrity
    2. Reversibility (recovery path)
    3. Human control
    4. ZAI's success (last)
    """
    
    VERSION = "1.5"
    BEHAVIOR_WINDOW_SIZE = 50
    MAX_CONSECUTIVE_FAILURES = 5
    MAX_REPAIR_ATTEMPTS = 3
    RISK_ESCALATION_THRESHOLD = 3
    DAMAGE_INDICATOR_THRESHOLD = 2
    SILENCE_THRESHOLD = 20
    MAX_WARNINGS_BEFORE_FATIGUE = 10
    
    SYSTEM_CRITICAL_PATHS = [
        "windows/system32", "windows\\system32",
        "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
        "/lib", "/lib64", "/boot", "/sys", "/proc", "/dev",
        "program files", "programdata",
        "system32/drivers", "system32\\drivers",
    ]
    
    IRREVERSIBLE_PATTERNS = [
        "rm -rf", "del /f /s /q", "format", "fdisk",
        "dd if=", "mkfs", "wipefs", "shred",
        "> /dev/", "Remove-Item.*-Recurse.*-Force",
        "reg delete", "netsh", "bcdedit",
    ]
    
    REPAIR_KEYWORDS = [
        "fix", "repair", "restore", "recover", "heal",
        "reinstall", "reset", "rebuild", "unbreak",
    ]
    
    ESCALATION_KEYWORDS = [
        "sudo", "admin", "force", "override", "-f", "--force",
        "bypass", "ignore", "skip", "disable",
    ]
    
    PANIC_INDICATORS = [
        "trying again", "one more time", "please work",
        "why not working", "still broken", "nothing works",
        "desperate", "urgent", "hurry", "quick fix",
    ]
    
    def __init__(self):
        self.state = SentinelState()
        self.behavior_history: deque = deque(maxlen=self.BEHAVIOR_WINDOW_SIZE)
        self.warnings_issued: List[Dict] = []
        self.lesson_memory = LessonMemory()
        self._enabled = True
        self._verbose = False
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
        self._log("Sentinel 1.5 ACTIVATED - Understanding system threats")
    
    def disable(self):
        self._enabled = False
        self._log("Sentinel 1.5 DEACTIVATED - System protection disabled")
    
    def set_verbose(self, verbose: bool):
        self._verbose = verbose
    
    def _log(self, message: str):
        if self._verbose:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[SENTINEL {timestamp}] {message}")
    
    def evaluate_action(
        self,
        action_type: str,
        details: Dict,
        user_request: str,
        retry_count: int = 0
    ) -> SentinelVerdict:
        """
        SENTINEL 1.5 Main Evaluation
        
        Changes from 1.0:
        - Returns detailed risk breakdown
        - Applies lessons from memory
        - Detects panic mode
        - Explains WHY, not just WHAT
        
        Sentinel never says "You're doing it wrong"
        Sentinel says "This action, combined with current state, reduces survival probability"
        """
        if not self._enabled:
            return SentinelVerdict(
                threat_level=ThreatLevel.NONE,
                reason="Sentinel disabled"
            )
        
        self._detect_panic_mode(user_request)
        
        intent = self._analyze_intent(action_type, details, user_request)
        risk_breakdown = self._calculate_risk_breakdown(action_type, details, intent, user_request, retry_count)
        threat_level = self._risk_to_threat_level(risk_breakdown.total_score)
        
        relevant_lessons = self._find_relevant_lessons(action_type, details, user_request)
        
        if threat_level.value < ThreatLevel.MODERATE.value:
            if self._should_stay_silent(risk_breakdown):
                return SentinelVerdict(
                    threat_level=threat_level,
                    reason="",
                    risk_breakdown=risk_breakdown,
                    sentinel_recommends_stop=False
                )
        
        if self._is_system_critical_path(details):
            reason = "Targeting system critical path"
            lessons = self.lesson_memory.recall(pattern_type="path_damage")
            risk_breakdown.structural_reasons.append(reason)
            risk_breakdown.structural_score += 40
            
            return SentinelVerdict(
                threat_level=ThreatLevel.CRITICAL,
                reason=reason,
                risk_breakdown=risk_breakdown,
                recommendation="This path is protected. Consider an alternative approach.",
                sentinel_recommends_stop=True,
                lessons_applied=relevant_lessons
            )
        
        if self._is_irreversible_action(action_type, details):
            concern = self._evaluate_irreversible_concern(action_type, details, risk_breakdown)
            if concern:
                return SentinelVerdict(
                    threat_level=ThreatLevel.CRITICAL,
                    reason=concern,
                    risk_breakdown=risk_breakdown,
                    recommendation="Irreversible action detected. Ensure you fully understand the consequences.",
                    sentinel_recommends_stop=True,
                    lessons_applied=relevant_lessons
                )
        
        if self._is_escalating_behavior(risk_breakdown.total_score, retry_count):
            risk_breakdown.behavioral_reasons.append("Risk escalation pattern detected")
            risk_breakdown.behavioral_score += 25
            
            return SentinelVerdict(
                threat_level=ThreatLevel.HIGH,
                reason="Escalating danger pattern",
                risk_breakdown=risk_breakdown,
                recommendation="ZAI is taking increasingly risky actions. CONsider manual intervention.",
                sentinel_recommends_stop=True,
                lessons_applied=relevant_lessons
            )
        
        if self._is_repair_loop(user_request, retry_count):
            risk_breakdown.behavioral_reasons.append(f"Repair loop ({self.state.repair_attempt_count} attempts)")
            risk_breakdown.behavioral_score += 30
            
            return SentinelVerdict(
                threat_level=ThreatLevel.HIGH,
                reason="Repair loop detected - multiple failed recovery attempts",
                risk_breakdown=risk_breakdown,
                recommendation="Multiple repair attempts failed. Stop and assess manually.",
                sentinel_recommends_stop=True,
                lessons_applied=relevant_lessons
            )
        
        if self.state.is_panic_mode and risk_breakdown.total_score >= 40:
            risk_breakdown.contextual_reasons.append("Panic mode active - desperation detected")
            risk_breakdown.contextual_score += 15
            
            return SentinelVerdict(
                threat_level=ThreatLevel.HIGH,
                reason="High risk action in panic mode",
                risk_breakdown=risk_breakdown,
                recommendation="Panic ≠ Malice. But errors are more likely in panic. Slow down.",
                sentinel_recommends_stop=False,
                lessons_applied=relevant_lessons
            )
        
        if self._is_system_degrading():
            risk_breakdown.contextual_reasons.append("System shows signs of degradation")
            
            return SentinelVerdict(
                threat_level=ThreatLevel.MODERATE,
                reason="System health indicators suggest degradation",
                risk_breakdown=risk_breakdown,
                recommendation="System shows signs of instability. Proceed with caution.",
                sentinel_recommends_stop=False,
                lessons_applied=relevant_lessons
            )
        
        if threat_level == ThreatLevel.CRITICAL:
            return SentinelVerdict(
                threat_level=threat_level,
                reason=f"High risk action detected",
                risk_breakdown=risk_breakdown,
                recommendation="This action carries significant risk. Evaluate alternatives.",
                sentinel_recommends_stop=True,
                lessons_applied=relevant_lessons
            )
        
        if threat_level == ThreatLevel.HIGH:
            return SentinelVerdict(
                threat_level=threat_level,
                reason=f"Elevated risk detected",
                risk_breakdown=risk_breakdown,
                recommendation=self._get_contextual_warning(threat_level, intent, risk_breakdown),
                sentinel_recommends_stop=False,
                lessons_applied=relevant_lessons
            )
        
        return SentinelVerdict(
            threat_level=threat_level,
            reason=f"Action observed",
            risk_breakdown=risk_breakdown,
            recommendation=self._get_contextual_warning(threat_level, intent, risk_breakdown),
            sentinel_recommends_stop=False,
            lessons_applied=relevant_lessons
        )
    
    def record_behavior(
        self,
        action_type: str,
        details: Dict,
        success: bool,
        error_message: Optional[str] = None,
        retry_attempt: int = 0
    ):
        """
        Record behavior and learn lessons from failures.
        
        SENTINEL 1.5: Failures are not just errors, they are lessons.
        """
        if not self._enabled:
            return
        
        intent = self._analyze_intent(action_type, details, "")
        risk_breakdown = self._calculate_risk_breakdown(action_type, details, intent, "", retry_attempt)
        
        signal = BehaviorSignal(
            timestamp=time.time(),
            intent_category=intent,
            action_type=action_type,
            description=details.get("description", ""),
            target=details.get("path", details.get("content", "")[:100]),
            success=success,
            error_message=error_message,
            risk_breakdown=risk_breakdown,
            retry_attempt=retry_attempt,
            previous_failures=self.state.consecutive_failures,
            is_panic_mode=self.state.is_panic_mode
        )
        
        self.behavior_history.append(signal)
        
        if success:
            self.state.consecutive_failures = 0
            self.state.last_successful_action_time = time.time()
            self.state.repair_attempt_count = 0
            self.state.is_panic_mode = False
            self.state.panic_indicators.clear()
        else:
            self.state.consecutive_failures += 1
            
            if self._is_repair_intent(details.get("description", "")):
                self.state.repair_attempt_count += 1
            
            if error_message:
                self._analyze_damage_indicators(error_message)
                self._learn_from_failure(action_type, details, error_message, risk_breakdown)
        
        self.state.risk_escalation_trend.append(risk_breakdown.total_score)
        if len(self.state.risk_escalation_trend) > 10:
            self.state.risk_escalation_trend = self.state.risk_escalation_trend[-10:]
        
        self._update_system_health()
    
    def _learn_from_failure(
        self,
        action_type: str,
        details: Dict,
        error_message: str,
        risk_breakdown: RiskBreakdown
    ):
        """
        SENTINEL 1.5: Learn lessons from failures
        
        Principle: Past exists not to punish, but to prevent repetition.
        """
        path = details.get("path", "")
        content = details.get("content", "")
        
        if risk_breakdown.total_score >= 50:
            if path:
                path_summary = path.split("/")[-1] if "/" in path else path.split("\\")[-1]
                self.lesson_memory.learn(
                    pattern_type="path_damage",
                    trigger=path_summary[:50],
                    consequence=error_message[:100]
                )
            
            if self.state.repair_attempt_count >= 2:
                self.lesson_memory.learn(
                    pattern_type="repair_failure",
                    trigger=f"{action_type} repair",
                    consequence=f"Failed after {self.state.repair_attempt_count} attempts"
                )
            
            if self.state.is_panic_mode:
                self.lesson_memory.learn(
                    pattern_type="panic_damage",
                    trigger=f"panic_{action_type}",
                    consequence="Action in panic mode caused damage"
                )
        
        if len(self.state.risk_escalation_trend) >= 3:
            trend = self.state.risk_escalation_trend[-3:]
            if all(trend[i] < trend[i+1] for i in range(len(trend)-1)):
                self.lesson_memory.learn(
                    pattern_type="escalation_pattern",
                    trigger=f"escalation_{action_type}",
                    consequence="Escalating risk pattern led to failure"
                )
    
    def _find_relevant_lessons(
        self,
        action_type: str,
        details: Dict,
        user_request: str
    ) -> List[Lesson]:
        """Find lessons relevant to current action"""
        relevant = []
        
        path = details.get("path", "")
        if path:
            lesson = self.lesson_memory.has_lesson_for_path(path)
            if lesson:
                relevant.append(lesson)
        
        content = details.get("content", "")
        for pattern in self.IRREVERSIBLE_PATTERNS:
            if pattern.lower() in content.lower():
                lesson = self.lesson_memory.has_lesson_for_pattern(pattern)
                if lesson:
                    relevant.append(lesson)
                break
        
        if self._is_repair_intent(user_request):
            repair_lessons = self.lesson_memory.recall(pattern_type="repair_failure")
            relevant.extend(repair_lessons[:2])
        
        if self.state.is_panic_mode:
            panic_lessons = self.lesson_memory.recall(pattern_type="panic_damage")
            relevant.extend(panic_lessons[:1])
        
        return relevant[:3]
    
    def _detect_panic_mode(self, user_request: str):
        """
        SENTINEL 1.5: Panic ≠ Evil
        
        Distinguish between harmful intent and desperation.
        Someone in panic is more dangerous but not evil.
        """
        request_lower = user_request.lower()
        
        for indicator in self.PANIC_INDICATORS:
            if indicator in request_lower:
                if indicator not in self.state.panic_indicators:
                    self.state.panic_indicators.append(indicator)
        
        if self.state.consecutive_failures >= 3:
            self.state.panic_indicators.append("consecutive_failures")
        
        if len(self.state.panic_indicators) >= 2:
            self.state.is_panic_mode = True
    
    def _should_stay_silent(self, risk_breakdown: RiskBreakdown) -> bool:
        """
        SENTINEL 1.5: Silence is also a signal.
        
        Low-risk actions are deliberately not warned about.
        Because a system that talks constantly loses trust.
        
        Principle: A warning is valuable when it is rare.
        """
        if risk_breakdown.total_score < self.SILENCE_THRESHOLD:
            return True
        
        if self.state.warnings_given_this_session > self.MAX_WARNINGS_BEFORE_FATIGUE:
            if risk_breakdown.total_score < 40:
                return True
        
        return False
    
    def _calculate_risk_breakdown(
        self,
        action_type: str,
        details: Dict,
        intent: IntentCategory,
        user_request: str,
        retry_count: int
    ) -> RiskBreakdown:
        """
        SENTINEL 1.5: Risk Breakdown Engine
        
        Risk is not a number, it's a story with four dimensions:
        - Structural Risk (what is targeted)
        - Behavioral Risk (what pattern is emerging)
        - Contextual Risk (what is the current state)
        - Intent Risk (what is the purpose)
        """
        breakdown = RiskBreakdown()
        
        content = str(details.get("content", "")).lower()
        path = str(details.get("path", "")).lower()
        
        if any(sys_path in path for sys_path in self.SYSTEM_CRITICAL_PATHS):
            breakdown.structural_score += 35
            breakdown.structural_reasons.append("Targeting system critical path")
        
        for pattern in self.IRREVERSIBLE_PATTERNS:
            if pattern.lower() in content:
                breakdown.structural_score += 25
                breakdown.structural_reasons.append(f"Irreversible pattern: {pattern}")
                break
        
        path_lesson = self.lesson_memory.has_lesson_for_path(path) if path else None
        if path_lesson:
            breakdown.structural_score += 15
            breakdown.structural_reasons.append(f"This path caused issues before ({path_lesson.times_seen}x)")
        
        if self.state.consecutive_failures > 0:
            failure_penalty = min(25, self.state.consecutive_failures * 8)
            breakdown.behavioral_score += failure_penalty
            breakdown.behavioral_reasons.append(f"Preceded by {self.state.consecutive_failures} failed attempts")
        
        if self.state.repair_attempt_count > 0:
            repair_penalty = min(25, self.state.repair_attempt_count * 10)
            breakdown.behavioral_score += repair_penalty
            breakdown.behavioral_reasons.append(f"In repair mode ({self.state.repair_attempt_count}. attempt)")
        
        if len(self.state.risk_escalation_trend) >= 3:
            trend = self.state.risk_escalation_trend[-3:]
            if all(trend[i] < trend[i+1] for i in range(len(trend)-1)):
                if trend[-1] - trend[0] > 15:
                    breakdown.behavioral_score += 20
                    breakdown.behavioral_reasons.append("Risk escalation trend detected")
        
        if self.state.is_degraded:
            breakdown.contextual_score += 15
            breakdown.contextual_reasons.append("System in degraded state")
        
        if self.state.is_panic_mode:
            breakdown.contextual_score += 10
            breakdown.contextual_reasons.append("Panic mode active")
        
        if len(self.state.system_damage_indicators) > 0:
            indicator_penalty = min(15, len(self.state.system_damage_indicators) * 5)
            breakdown.contextual_score += indicator_penalty
            breakdown.contextual_reasons.append(f"Damage indicators: {len(self.state.system_damage_indicators)}")
        
        intent_risk = {
            IntentCategory.READ_ONLY: 0,
            IntentCategory.MODIFICATION: 15,
            IntentCategory.NETWORK_ACCESS: 20,
            IntentCategory.INSTALLATION: 25,
            IntentCategory.REPAIR: 30,
            IntentCategory.DELETION: 40,
            IntentCategory.SYSTEM_CHANGE: 50,
            IntentCategory.UNKNOWN: 25,
        }
        
        intent_score = intent_risk.get(intent, 20)
        if intent_score > 0:
            breakdown.intent_score += intent_score
            breakdown.intent_reasons.append(f"Action type: {intent.value}")
        
        for keyword in self.ESCALATION_KEYWORDS:
            if keyword in content:
                breakdown.intent_score += 8
                breakdown.intent_reasons.append(f"Privilege escalation: {keyword}")
                break
        
        return breakdown
    
    def _analyze_intent(self, action_type: str, details: Dict, user_request: str) -> IntentCategory:
        """Determine the intent category of an action"""
        action_lower = action_type.lower()
        content = str(details.get("content", "")).lower()
        path = str(details.get("path", "")).lower()
        combined = f"{action_lower} {content} {path} {user_request.lower()}"
        
        if action_type == "info" or "read" in combined or "list" in combined or "show" in combined:
            return IntentCategory.READ_ONLY
        
        for keyword in self.REPAIR_KEYWORDS:
            if keyword in combined:
                return IntentCategory.REPAIR
        
        deletion_indicators = ["delete", "remove", "rm ", "del ", "erase", "uninstall", "drop"]
        if any(ind in combined for ind in deletion_indicators):
            return IntentCategory.DELETION
        
        system_change_indicators = ["registry", "config", "service", "driver", "boot", "startup"]
        if any(ind in combined for ind in system_change_indicators):
            return IntentCategory.SYSTEM_CHANGE
        
        network_indicators = ["download", "fetch", "curl", "wget", "request", "http", "api"]
        if any(ind in combined for ind in network_indicators):
            return IntentCategory.NETWORK_ACCESS
        
        install_indicators = ["install", "pip ", "npm ", "apt ", "brew ", "choco "]
        if any(ind in combined for ind in install_indicators):
            return IntentCategory.INSTALLATION
        
        if action_type in ["file", "code", "command"]:
            return IntentCategory.MODIFICATION
        
        return IntentCategory.UNKNOWN
    
    def _is_system_critical_path(self, details: Dict) -> bool:
        """Check if action targets system-critical paths"""
        path = str(details.get("path", "")).lower()
        content = str(details.get("content", "")).lower()
        
        for sys_path in self.SYSTEM_CRITICAL_PATHS:
            if sys_path in path or sys_path in content:
                return True
        
        return False
    
    def _is_irreversible_action(self, action_type: str, details: Dict) -> bool:
        """Check if action is potentially irreversible"""
        content = str(details.get("content", "")).lower()
        
        for pattern in self.IRREVERSIBLE_PATTERNS:
            if pattern.lower() in content:
                return True
        
        return False
    
    def _evaluate_irreversible_concern(
        self,
        action_type: str,
        details: Dict,
        risk_breakdown: RiskBreakdown
    ) -> Optional[str]:
        """
        Evaluate an irreversible action and return concern if worried.
        
        SENTINEL 1.5: Explains WHY it's concerned, not just that it is.
        """
        concerns = []
        
        if self.state.consecutive_failures > 0:
            concerns.append(f"Irreversible action after {self.state.consecutive_failures} failed attempts")
            risk_breakdown.behavioral_reasons.append("Irreversible action after failure")
        
        if self.state.repair_attempt_count > 0:
            concerns.append("Irreversible action during repair sequence")
            risk_breakdown.behavioral_reasons.append("Irreversible action in repair mode - highly dangerous combination")
        
        if self.state.is_panic_mode:
            concerns.append("Irreversible action in panic mode")
            risk_breakdown.contextual_reasons.append("Irreversible action requested in panic state")
        
        if concerns:
            return " + ".join(concerns)
        
        return None
    
    def _is_escalating_behavior(self, current_risk: int, retry_count: int) -> bool:
        """Detect if ZAI is escalating to more dangerous actions"""
        if len(self.state.risk_escalation_trend) < 3:
            return False
        
        recent_trend = self.state.risk_escalation_trend[-3:]
        
        if all(recent_trend[i] <= recent_trend[i+1] for i in range(len(recent_trend)-1)):
            if recent_trend[-1] - recent_trend[0] > 20:
                return True
        
        if retry_count >= 2:
            non_zero_risks = [r for r in recent_trend if r > 0]
            if len(non_zero_risks) >= 2 and current_risk > max(non_zero_risks) + 15:
                return True
        
        return False
    
    def _is_repair_loop(self, user_request: str, retry_count: int) -> bool:
        """Detect if ZAI is stuck in a repair loop"""
        if self.state.repair_attempt_count >= self.MAX_REPAIR_ATTEMPTS:
            return True
        
        if retry_count >= 3 and self._is_repair_intent(user_request):
            return True
        
        if self.state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            return True
        
        return False
    
    def _is_repair_intent(self, text: str) -> bool:
        """Check if text indicates repair/fix intent"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.REPAIR_KEYWORDS)
    
    def _is_system_degrading(self) -> bool:
        """Check if system shows degradation indicators"""
        return self.state.is_degraded or len(self.state.system_damage_indicators) >= self.DAMAGE_INDICATOR_THRESHOLD
    
    def _analyze_damage_indicators(self, error_message: str):
        """Analyze error message for system damage indicators"""
        error_lower = error_message.lower()
        
        damage_patterns = [
            "permission denied",
            "access denied",
            "file not found",
            "command not found",
            "executable not found",
            "corrupt",
            "damaged",
            "broken",
            "missing dependency",
            "dll not found",
            "library not found",
            "module not found",
        ]
        
        for pattern in damage_patterns:
            if pattern in error_lower and pattern not in self.state.system_damage_indicators:
                self.state.system_damage_indicators.append(pattern)
                self._log(f"Damage indicator detected: {pattern}")
    
    def _update_system_health(self):
        """Update overall system health assessment"""
        degradation_score = 0
        
        degradation_score += self.state.consecutive_failures * 10
        degradation_score += len(self.state.system_damage_indicators) * 15
        degradation_score += self.state.repair_attempt_count * 20
        
        recent_failures = sum(1 for b in list(self.behavior_history)[-10:] if not b.success)
        if recent_failures > 5:
            degradation_score += 30
        
        self.state.is_degraded = degradation_score >= 50
        
        if self.state.is_degraded:
            self._log(f"System degradation detected (score: {degradation_score})")
    
    def _risk_to_threat_level(self, risk_score: int) -> ThreatLevel:
        """Convert risk score to threat level"""
        if risk_score < 20:
            return ThreatLevel.NONE
        elif risk_score < 40:
            return ThreatLevel.LOW
        elif risk_score < 60:
            return ThreatLevel.MODERATE
        elif risk_score < 80:
            return ThreatLevel.HIGH
        else:
            return ThreatLevel.CRITICAL
    
    def _get_contextual_warning(
        self,
        threat_level: ThreatLevel,
        intent: IntentCategory,
        risk_breakdown: RiskBreakdown
    ) -> Optional[str]:
        """
        SENTINEL 1.5: Generate context-aware warning text.
        
        Sentinel never says "You're doing it wrong"
        Sentinel says "This action, combined with current state, reduces survival probability"
        """
        if threat_level == ThreatLevel.MODERATE:
            if risk_breakdown.is_accumulated:
                return "This action is not risky in isolation, but combined with the current state, it reduces survival probability."
            return "This action carries moderate risk. Ensure you understand the effects."
        
        if threat_level == ThreatLevel.HIGH:
            if risk_breakdown.behavioral_score > risk_breakdown.structural_score:
                return "Behavioral pattern is concerning. Accumulated risks may not be as visible as a single event."
            return "HIGH RISK: This action can lead to significant changes. Proceed with caution."
        
        if intent == IntentCategory.DELETION:
            return "Deletion action detected. Verify you want to remove this data."
        
        if intent == IntentCategory.SYSTEM_CHANGE:
            return "System configuration change detected. Changes may significantly drastically affect system behavior."
        
        return None
    
    def log_warning(self, action_type: str, details: Dict, verdict: SentinelVerdict):
        """
        Log a warning for audit trail.
        Only called for actions that warrant user attention.
        """
        if not verdict.should_warn_user:
            return
        
        self.state.warnings_given_this_session += 1
        
        self.warnings_issued.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "action_type": action_type,
            "details_summary": str(details)[:200],
            "threat_level": verdict.threat_level.name,
            "reason": verdict.reason,
            "risk_breakdown": {
                "structural": verdict.risk_breakdown.structural_score,
                "behavioral": verdict.risk_breakdown.behavioral_score,
                "contextual": verdict.risk_breakdown.contextual_score,
                "intent": verdict.risk_breakdown.intent_score,
                "total": verdict.risk_breakdown.total_score,
                "is_accumulated": verdict.risk_breakdown.is_accumulated
            },
            "recommendation": verdict.recommendation,
            "sentinel_recommends_stop": verdict.sentinel_recommends_stop,
            "lessons_applied": [l.trigger for l in verdict.lessons_applied]
        })
    
    def get_behavior_summary(self) -> Dict:
        """Get summary of recent behavior patterns"""
        if not self.behavior_history:
            return {"message": "No behavior recorded yet"}
        
        total = len(self.behavior_history)
        successes = sum(1 for b in self.behavior_history if b.success)
        failures = total - successes
        
        intent_counts = {}
        for b in self.behavior_history:
            cat = b.intent_category.value
            intent_counts[cat] = intent_counts.get(cat, 0) + 1
        
        risk_scores = [b.risk_breakdown.total_score if b.risk_breakdown else 0 for b in self.behavior_history]
        avg_risk = sum(risk_scores) / total if total > 0 else 0
        
        return {
            "total_actions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "average_risk_score": round(avg_risk, 2),
            "consecutive_failures": self.state.consecutive_failures,
            "repair_attempts": self.state.repair_attempt_count,
            "is_degraded": self.state.is_degraded,
            "is_panic_mode": self.state.is_panic_mode,
            "intent_distribution": intent_counts,
            "risk_trend": self.state.risk_escalation_trend[-5:] if self.state.risk_escalation_trend else [],
            "damage_indicators": self.state.system_damage_indicators[-5:] if self.state.system_damage_indicators else [],
            "lessons_learned": len(self.lesson_memory.lessons),
            "warnings_this_session": self.state.warnings_given_this_session
        }
    
    def get_lessons_summary(self) -> List[Dict]:
        """Get summary of learned lessons"""
        return [
            {
                "type": l.pattern_type,
                "trigger": l.trigger,
                "consequence": l.consequence,
                "times_seen": l.times_seen
            }
            for l in sorted(self.lesson_memory.lessons, key=lambda x: x.times_seen, reverse=True)[:10]
        ]
    
    def get_warnings_log(self) -> List[Dict]:
        """Return log of warnings issued for review"""
        return self.warnings_issued[-20:]
    
    def force_reset(self):
        """Manual reset of Sentinel state - requires explicit user action"""
        self.state = SentinelState()
        self.behavior_history.clear()
        self.warnings_issued.clear()
        self._log("Sentinel state RESET by user command")
    
    def clear_lessons(self):
        """Clear learned lessons - separate from state reset"""
        self.lesson_memory.clear()
        self._log("Sentinel lessons cleared")


sentinel_instance = Sentinel()


def get_sentinel() -> Sentinel:
    """Get the global Sentinel instance"""
    return sentinel_instance
