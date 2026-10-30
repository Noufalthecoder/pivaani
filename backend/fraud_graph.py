import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Tuple, Optional
import logging

logger = logging.getLogger("pivaani.fraud_graph")

class FraudGraph:
    """
    Graph-based fraud detection engine using NetworkX.
    Identifies collusive fraud rings where a single customer VPA coordinates
    stuck payments across multiple distinct merchant VPAs within a 5-minute sliding window.
    """

    def __init__(self, window_seconds: int = 300, merchant_threshold: int = 3):
        self.graph = nx.Graph()
        self.window_seconds = window_seconds  # 5 minutes
        self.merchant_threshold = merchant_threshold  # > 3 distinct merchants
        self.flagged_fraud_rings: Set[str] = set()

        # In-memory incident ledger: customer_vpa -> list of incidents
        self._incidents: Dict[str, List[Dict[str, Any]]] = {}

    def add_stuck_payment_incident(
        self,
        customer_vpa: str,
        merchant_vpa: str,
        case_id: str,
        timestamp: Optional[datetime] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Records a stuck payment case into the graph.
        Adds/updates edge between customer_vpa and merchant_vpa.
        Checks if customer connects to > 3 different merchants within 5 minutes.
        Returns: (is_newly_flagged, fraud_payload_if_flagged)
        """
        now = timestamp or datetime.utcnow()

        # 1. Update NetworkX graph nodes & edge
        if not self.graph.has_node(customer_vpa):
            self.graph.add_node(customer_vpa, type="customer", is_fraud_ring=False)
        if not self.graph.has_node(merchant_vpa):
            self.graph.add_node(merchant_vpa, type="merchant", is_fraud_ring=False)

        if self.graph.has_edge(customer_vpa, merchant_vpa):
            edge_data = self.graph[customer_vpa][merchant_vpa]
            edge_data["weight"] = edge_data.get("weight", 0) + 1
            if case_id not in edge_data.get("cases", []):
                edge_data["cases"].append(case_id)
            edge_data["last_seen"] = now.isoformat()
        else:
            self.graph.add_edge(
                customer_vpa,
                merchant_vpa,
                weight=1,
                cases=[case_id],
                first_seen=now.isoformat(),
                last_seen=now.isoformat()
            )

        # 2. Append to chronological incident ledger
        if customer_vpa not in self._incidents:
            self._incidents[customer_vpa] = []

        self._incidents[customer_vpa].append({
            "merchant_vpa": merchant_vpa,
            "case_id": case_id,
            "timestamp": now
        })

        # 3. Analyze sliding 5-minute window for collusive rings
        cutoff = now - timedelta(seconds=self.window_seconds)
        # Keep only incidents within the active sliding window
        recent_incidents = [
            inc for inc in self._incidents[customer_vpa]
            if inc["timestamp"] >= cutoff
        ]
        self._incidents[customer_vpa] = recent_incidents

        # Distinct merchants connected to within the window
        connected_merchants = {inc["merchant_vpa"] for inc in recent_incidents}

        logger.info(
            f"🔍 Graph Analysis for {customer_vpa}: {len(connected_merchants)} "
            f"distinct merchants with stuck payments in 5m window (threshold: >{self.merchant_threshold})"
        )

        # 4. Check Fraud Ring condition: > 3 distinct merchants
        if len(connected_merchants) > self.merchant_threshold:
            is_new = customer_vpa not in self.flagged_fraud_rings
            self.flagged_fraud_rings.add(customer_vpa)
            self.graph.nodes[customer_vpa]["is_fraud_ring"] = True

            fraud_payload = {
                "customer_vpa": customer_vpa,
                "connected_merchants": list(connected_merchants),
                "merchant_count": len(connected_merchants),
                "threshold": self.merchant_threshold,
                "window_seconds": self.window_seconds,
                "case_id": case_id,
                "reason": "Fraud Ring Detected: Collusive retap pattern across > 3 distinct merchants",
                "detected_at": now.isoformat()
            }

            if is_new:
                logger.warning(f"🚨 FRAUD RING FLAGGED: {customer_vpa} across {len(connected_merchants)} merchants!")

            return is_new, fraud_payload

        return False, None

    def is_flagged(self, customer_vpa: str) -> bool:
        """Checks if a Customer VPA has been flagged as a fraudulent collusive ring"""
        return customer_vpa in self.flagged_fraud_rings

    def get_fraud_ring_snapshot(self, customer_vpa: str) -> Dict[str, Any]:
        """Returns localized graph neighborhood for the flagged customer"""
        neighbors = list(self.graph.neighbors(customer_vpa)) if self.graph.has_node(customer_vpa) else []
        return {
            "customer_vpa": customer_vpa,
            "connected_merchants": neighbors,
            "merchant_count": len(neighbors),
            "flagged": self.is_flagged(customer_vpa),
            "incident_count": len(self._incidents.get(customer_vpa, []))
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entire graph topology to JSON-compatible dictionary"""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({
                "id": n,
                "label": n,
                "type": data.get("type", "unknown"),
                "is_fraud_ring": data.get("is_fraud_ring", False),
                "degree": self.graph.degree(n)
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
                "cases": data.get("cases", []),
                "last_seen": data.get("last_seen", None)
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "flagged_fraud_rings": list(self.flagged_fraud_rings),
            "summary": {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "flagged_count": len(self.flagged_fraud_rings)
            }
        }

    def reset(self):
        """Resets the fraud graph and clears flagged rings"""
        self.graph.clear()
        self.flagged_fraud_rings.clear()
        self._incidents.clear()

# Global singleton FraudGraph detector
fraud_detector = FraudGraph()

