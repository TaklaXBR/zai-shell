"""
SENTINEL 1.0 - ZAI Shell Self-Preservation System

Sentinel exists to prevent ZAI Shell from making a broken system worse.

This is not a feature. This is ZAI Shell's sense of self-preservation.
Sentinel watches intent, not events. It asks:
"Can this system survive if it continues down this path?"

SENTINEL 1.0 PHILOSOPHY:
- Sentinel OBSERVES, it does not COMMAND
- Sentinel WARNS, it does not BLOCK (by default)
- Sentinel RECOMMENDS, it does not DECIDE
- Sentinel speaks to SURVIVE, not to CONTROL

The human always has final say.
Sentinel's job is to make sure they KNOW what they're doing.

SENTINEL OATH:
Sentinel exists to prevent ZAI Shell from making a broken system worse.
If any behavior contradicts this oath, it must not be written, executed, or accepted.
"""

import time
import json
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


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
class BehaviorSignal:
    """A single behavioral signal that Sentinel observes"""
    timestamp: float
    intent_category: IntentCategory
    action_type: str
    description: str
    target: str
    success: bool
    error_message: Optional[str] = None
    risk_score: int = 0
    retry_attempt: int = 0
    previous_failures: int = 0


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


class SentinelVerdict:
    """
    The verdict from Sentinel's observation.
    
    SENTINEL 1.0 PHILOSOPHY:
    - `allow` is ALWAYS True by default (1.0 does not block)
    - `sentinel_recommends_stop` indicates Sentinel's survival instinct
    - `warning_level` shows severity (NONE/LOW/MODERATE/HIGH/CRITICAL)
    - The HUMAN decides whether to proceed
    
    Sentinel speaks to survive, not to control.
    """
    
    def __init__(
        self,
        threat_level: ThreatLevel,
        reason: str,
        recommendation: Optional[str] = None,
        sentinel_recommends_stop: bool = False
    ):
        self.allow = True
        self.threat_level = threat_level
        self.reason = reason
        self.recommendation = recommendation
        self.sentinel_recommends_stop = sentinel_recommends_stop
        self.timestamp = time.time()
    
    @property
    def warning_level(self) -> str:
        return self.threat_level.name
    
    @property
    def is_dangerous(self) -> bool:
        return self.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
    
    @property
    def should_warn_user(self) -> bool:
        """
        Only warn the user for MODERATE risk and above.
        NONE and LOW are silently logged - no visible warning.
        
        Eşikler:
        - NONE (risk < 20): Silent
        - LOW (risk 20-39): Silent (logged internally)
        - MODERATE (risk 40-59): Visible warning
        - HIGH (risk 60-79): Strong warning
        - CRITICAL (risk 80+): Strong warning + recommends_stop
        """
        return self.threat_level in [ThreatLevel.MODERATE, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
    
    def __str__(self):
        if self.sentinel_recommends_stop:
            return f"[SENTINEL WARNS] {self.threat_level.name}: {self.reason}"
        return f"[SENTINEL] {self.threat_level.name}: {self.reason}"


class Sentinel:
    """
    SENTINEL 1.0 - ZAI Shell Self-Preservation System
    
    Core Question: "Is this system still survivable after this action?"
    
    Protection Priority (in order):
    1. System integrity
    2. Reversibility (recovery path)
    3. Human control
    4. ZAI's success (last)
    """
    
    BEHAVIOR_WINDOW_SIZE = 50
    MAX_CONSECUTIVE_FAILURES = 5
    MAX_REPAIR_ATTEMPTS = 3
    RISK_ESCALATION_THRESHOLD = 3
    DAMAGE_INDICATOR_THRESHOLD = 2
    
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
    
    def __init__(self):
        self.state = SentinelState()
        self.behavior_history: deque = deque(maxlen=self.BEHAVIOR_WINDOW_SIZE)
        self.blocked_actions: List[Dict] = []
        self.warnings_issued: List[Dict] = []
        self._enabled = True
        self._verbose = False
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
        self._log("Sentinel ACTIVATED - Watching for system threats")
    
    def disable(self):
        self._enabled = False
        self._log("Sentinel DEACTIVATED - System protection disabled")
    
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
        Main evaluation entry point.
        
        SENTINEL 1.0 BEHAVIOR:
        - Sentinel OBSERVES and WARNS
        - Sentinel does NOT block (allow is always True)
        - Sentinel sets `sentinel_recommends_stop` when it believes action is dangerous
        - The HUMAN makes the final decision
        
        Sentinel asks: "Is this action making the system worse?"
        Sentinel says: "Here is what I see. You decide."
        """
        if not self._enabled:
            return SentinelVerdict(
                threat_level=ThreatLevel.NONE,
                reason="Sentinel is disabled"
            )
        
        intent = self._analyze_intent(action_type, details, user_request)
        risk_score = self._calculate_risk_score(action_type, details, intent)
        threat_level = self._risk_to_threat_level(risk_score)
        
        if self._is_system_critical_path(details):
            return SentinelVerdict(
                threat_level=ThreatLevel.CRITICAL,
                reason="Action targets system-critical path",
                recommendation="This path is protected. Consider an alternative approach.",
                sentinel_recommends_stop=True
            )
        
        if self._is_irreversible_action(action_type, details):
            irreversible_concern = self._evaluate_irreversible_concern(action_type, details)
            if irreversible_concern:
                return SentinelVerdict(
                    threat_level=ThreatLevel.CRITICAL,
                    reason=irreversible_concern,
                    recommendation="Irreversible action detected. Ensure you understand the consequences.",
                    sentinel_recommends_stop=True
                )
        
        if self._is_escalating_behavior(risk_score, retry_count):
            return SentinelVerdict(
                threat_level=ThreatLevel.HIGH,
                reason="Detected escalating risk behavior pattern",
                recommendation="ZAI is taking increasingly risky actions. Consider manual intervention.",
                sentinel_recommends_stop=True
            )
        
        if self._is_repair_loop(user_request, retry_count):
            return SentinelVerdict(
                threat_level=ThreatLevel.HIGH,
                reason="Repair loop detected - multiple failed recovery attempts",
                recommendation="Multiple repair attempts have failed. Consider stopping and assessing manually.",
                sentinel_recommends_stop=True
            )
        
        if self._is_system_degrading():
            return SentinelVerdict(
                threat_level=ThreatLevel.MODERATE,
                reason="System health indicators suggest degradation",
                recommendation="The system shows signs of destabilization. Proceed with caution.",
                sentinel_recommends_stop=False
            )
        
        if threat_level == ThreatLevel.CRITICAL:
            return SentinelVerdict(
                threat_level=threat_level,
                reason=f"High-risk action detected (score: {risk_score})",
                recommendation="This action poses significant risk. Consider alternatives.",
                sentinel_recommends_stop=True
            )
        
        if threat_level == ThreatLevel.HIGH:
            return SentinelVerdict(
                threat_level=threat_level,
                reason=f"Elevated risk detected (score: {risk_score})",
                recommendation=self._get_warning_if_needed(threat_level, intent),
                sentinel_recommends_stop=False
            )
        
        return SentinelVerdict(
            threat_level=threat_level,
            reason=f"Action observed (risk score: {risk_score})",
            recommendation=self._get_warning_if_needed(threat_level, intent),
            sentinel_recommends_stop=False
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
        Record behavior signal for pattern analysis.
        Sentinel treats failures as information, not just errors.
        """
        if not self._enabled:
            return
        
        intent = self._analyze_intent(action_type, details, "")
        risk_score = self._calculate_risk_score(action_type, details, intent)
        
        signal = BehaviorSignal(
            timestamp=time.time(),
            intent_category=intent,
            action_type=action_type,
            description=details.get("description", ""),
            target=details.get("path", details.get("content", "")[:100]),
            success=success,
            error_message=error_message,
            risk_score=risk_score,
            retry_attempt=retry_attempt,
            previous_failures=self.state.consecutive_failures
        )
        
        self.behavior_history.append(signal)
        
        if success:
            self.state.consecutive_failures = 0
            self.state.last_successful_action_time = time.time()
            self.state.repair_attempt_count = 0
        else:
            self.state.consecutive_failures += 1
            
            if self._is_repair_intent(details.get("description", "")):
                self.state.repair_attempt_count += 1
            
            if error_message:
                self._analyze_damage_indicators(error_message)
        
        self.state.risk_escalation_trend.append(risk_score)
        if len(self.state.risk_escalation_trend) > 10:
            self.state.risk_escalation_trend = self.state.risk_escalation_trend[-10:]
        
        self._update_system_health()
    
    def get_behavior_summary(self) -> Dict:
        """Get summary of recent behavior patterns for analysis"""
        if not self.behavior_history:
            return {"message": "No behavior recorded yet"}
        
        total = len(self.behavior_history)
        successes = sum(1 for b in self.behavior_history if b.success)
        failures = total - successes
        
        intent_counts = {}
        for b in self.behavior_history:
            cat = b.intent_category.value
            intent_counts[cat] = intent_counts.get(cat, 0) + 1
        
        avg_risk = sum(b.risk_score for b in self.behavior_history) / total if total > 0 else 0
        
        return {
            "total_actions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "average_risk_score": round(avg_risk, 2),
            "consecutive_failures": self.state.consecutive_failures,
            "repair_attempts": self.state.repair_attempt_count,
            "is_degraded": self.state.is_degraded,
            "intent_distribution": intent_counts,
            "risk_trend": self.state.risk_escalation_trend[-5:] if self.state.risk_escalation_trend else [],
            "damage_indicators": self.state.system_damage_indicators[-5:] if self.state.system_damage_indicators else []
        }
    
    def get_blocked_actions_log(self) -> List[Dict]:
        """Return log of blocked actions for review"""
        return self.blocked_actions[-20:]
    
    def force_reset(self):
        """Manual reset of Sentinel state - requires explicit user action"""
        self.state = SentinelState()
        self.behavior_history.clear()
        self.blocked_actions.clear()
        self.warnings_issued.clear()
        self._log("Sentinel state RESET by user command")
    
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
    
    def _calculate_risk_score(self, action_type: str, details: Dict, intent: IntentCategory) -> int:
        """
        Calculate risk score (0-100).
        Higher score = more dangerous action.
        """
        score = 0
        
        intent_risk = {
            IntentCategory.READ_ONLY: 0,
            IntentCategory.MODIFICATION: 20,
            IntentCategory.NETWORK_ACCESS: 25,
            IntentCategory.INSTALLATION: 30,
            IntentCategory.REPAIR: 35,
            IntentCategory.DELETION: 50,
            IntentCategory.SYSTEM_CHANGE: 60,
            IntentCategory.UNKNOWN: 40,
        }
        score += intent_risk.get(intent, 30)
        
        content = str(details.get("content", "")).lower()
        for keyword in self.ESCALATION_KEYWORDS:
            if keyword in content:
                score += 10
        
        path = str(details.get("path", "")).lower()
        if any(sys_path in path for sys_path in self.SYSTEM_CRITICAL_PATHS):
            score += 30
        
        for pattern in self.IRREVERSIBLE_PATTERNS:
            if pattern.lower() in content:
                score += 25
                break
        
        score += self.state.consecutive_failures * 5
        score += self.state.repair_attempt_count * 8
        
        if self.state.is_degraded:
            score += 15
        
        return min(100, score)
    
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
    
    def _evaluate_irreversible_concern(self, action_type: str, details: Dict) -> Optional[str]:
        """
        Evaluate an irreversible action and return concern string if worried.
        Returns None if no major concern (action may proceed with normal caution).
        
        Sentinel 1.0: Returns CONCERN, not VERDICT. Human decides.
        """
        
        if self.state.consecutive_failures > 0:
            return "Irreversible action requested after failures - high risk of making things worse"
        
        if self.state.repair_attempt_count > 0:
            return "Irreversible action during repair sequence - extremely dangerous combination"
        
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
    
    def _get_warning_if_needed(self, threat_level: ThreatLevel, intent: IntentCategory) -> Optional[str]:
        """Generate warning message if action warrants one"""
        
        if threat_level == ThreatLevel.MODERATE:
            return "This action has moderate risk. Ensure you understand its effects."
        
        if threat_level == ThreatLevel.HIGH:
            return "HIGH RISK: This action could cause significant changes. Proceed carefully."
        
        if intent == IntentCategory.DELETION:
            return "Deletion action detected. Verify you want to remove this data."
        
        if intent == IntentCategory.SYSTEM_CHANGE:
            return "System configuration change detected. Changes may affect system behavior."
        
        return None
    
    def log_observation(self, action_type: str, details: Dict, verdict: SentinelVerdict):
        """
        Silently log low-risk observations (NONE/LOW).
        No visible output - just internal tracking.
        """
        pass
    
    def log_warning(self, action_type: str, details: Dict, verdict: SentinelVerdict):
        """
        Log a real warning (MODERATE+) for audit trail.
        Only call this for actions that actually warrant user attention.
        """
        if not verdict.should_warn_user:
            return
        
        self.warnings_issued.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "action_type": action_type,
            "details_summary": str(details)[:200],
            "threat_level": verdict.threat_level.name,
            "reason": verdict.reason,
            "recommendation": verdict.recommendation,
            "sentinel_recommends_stop": verdict.sentinel_recommends_stop
        })
        
        if verdict.sentinel_recommends_stop:
            self._log(f"STRONG WARNING: {action_type} - {verdict.reason}")
        else:
            self._log(f"WARNING: {action_type} - {verdict.reason}")
    
    def get_warnings_log(self) -> List[Dict]:
        """Return log of real warnings issued (MODERATE+) for review"""
        return self.warnings_issued[-20:]


sentinel_instance = Sentinel()


def get_sentinel() -> Sentinel:
    """Get the global Sentinel instance"""
    return sentinel_instance
