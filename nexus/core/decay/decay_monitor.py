"""
Assumption Decay Monitor - Phase 5
Monitors high-risk assumptions for decay signals
"""
import logging
from typing import List
import re

from nexus.models.dpr import DPR
from nexus.models.commit import CommitRecord
from nexus.models.decay import AssumptionDecayRecord

logger = logging.getLogger(__name__)

DECAY_SIGNALS = [
    "TODO: remove", "FIXME:", "HACK:", "deprecated", "obsolete",
    "no longer valid", "needs update", "revisit", "temporary",
    "workaround", "breaks on", "fails with"
]


class DecayMonitor:
    """
    Monitors assumptions for decay signals.
    
    Phase 5 of the Nexus pipeline:
    - Filters high-risk assumptions
    - Searches for decay signals in commits
    - Generates monitoring queries
    """
    
    async def analyze_decay(
        self,
        dprs: List[DPR],
        commits: List[CommitRecord]
    ) -> List[AssumptionDecayRecord]:
        """
        Analyze DPRs for assumption decay.
        
        Args:
            dprs: List of DPRs
            commits: List of commits
            
        Returns:
            List of AssumptionDecayRecords
        """
        logger.info(f"Analyzing {len(dprs)} DPRs for assumption decay")
        
        alerts = []
        
        # Filter high-risk DPRs
        high_risk_dprs = [dpr for dpr in dprs if dpr.assumption_decay_risk == "high"]
        
        logger.info(f"Found {len(high_risk_dprs)} high-risk DPRs")
        
        for dpr in high_risk_dprs:
            for assumption in dpr.implicit_assumptions:
                alert = await self._check_assumption(dpr, assumption, commits)
                if alert:
                    alerts.append(alert)
                    
        logger.info(f"Generated {len(alerts)} decay alerts")
        
        return alerts
        
    async def _check_assumption(
        self,
        dpr: DPR,
        assumption: str,
        commits: List[CommitRecord]
    ) -> AssumptionDecayRecord:
        """Check a single assumption for decay."""
        signals_found = []
        earliest_date = "not found"
        
        # Search commits for decay signals
        for commit in commits:
            message_lower = commit.message.lower()
            
            # Check if any decay signal is present
            for signal in DECAY_SIGNALS:
                if signal.lower() in message_lower:
                    signals_found.append(f"{commit.date.strftime('%Y-%m')}: {commit.message[:100]}")
                    if earliest_date == "not found":
                        earliest_date = commit.date.strftime('%Y-%m')
                        
        already_decaying = len(signals_found) >= 2
        
        return AssumptionDecayRecord(
            dpr_id=dpr.dpr_id,
            assumption=assumption,
            decay_signals_found=signals_found[:5],  # Limit to 5
            earliest_signal_date=earliest_date,
            already_decaying=already_decaying,
            decay_evidence=signals_found[0] if signals_found else "No decay signals found",
            recommended_monitor_query=self._generate_monitor_query(assumption)
        )
        
    def _generate_monitor_query(self, assumption: str) -> str:
        """Generate a monitoring query for an assumption."""
        # Extract key terms from assumption
        terms = re.findall(r'\b\w{4,}\b', assumption.lower())
        key_terms = [t for t in terms if t not in ['inferred', 'assumes', 'assumption']][:3]
        
        if key_terms:
            return f"Check commits mentioning: {', '.join(key_terms)}"
        else:
            return "Monitor commits for changes to this assumption"

# Made with Bob
