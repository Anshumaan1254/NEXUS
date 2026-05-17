"""
Nexus - Risk Report PDF Generator
Generates a professional PDF report using ReportLab.
Reads from nexus_data.json.
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def load_nexus_data():
    base = Path(__file__).resolve().parent.parent / "nexus-dashboard"
    p = base / "nexus_data.json"
    if not p.exists():
        print(f"nexus_data.json not found at {p}. Run the analysis pipeline first.")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def build_pdf(data):
    print("="*60+"\nNEXUS - RISK REPORT PDF GENERATOR\n"+"="*60)
    
    base = Path(__file__).resolve().parent.parent
    pdf_path = base / "nexus_risk_report.pdf"
    
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=30*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('NexusTitle', parent=styles['Title'], fontSize=24, spaceAfter=6, textColor=colors.HexColor('#1a1a2e'))
    subtitle_style = ParagraphStyle('NexusSub', parent=styles['Normal'], fontSize=12, spaceAfter=12, textColor=colors.HexColor('#555'))
    h2_style = ParagraphStyle('NexusH2', parent=styles['Heading2'], fontSize=16, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor('#16213e'))
    h3_style = ParagraphStyle('NexusH3', parent=styles['Heading3'], fontSize=13, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#0f3460'))
    body_style = ParagraphStyle('NexusBody', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    small_style = ParagraphStyle('NexusSmall', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    
    elements = []
    meta = data.get("metadata", {})
    
    # ── Title Page ─────────────────────────────────────
    elements.append(Spacer(1, 60))
    elements.append(Paragraph("NEXUS", title_style))
    elements.append(Paragraph("Causal Intelligence Platform — Risk Report", subtitle_style))
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor('#0f3460')))
    elements.append(Spacer(1, 20))
    
    info = [
        f"<b>Repository:</b> {meta.get('repository', 'N/A')}",
        f"<b>Analysis Window:</b> {meta.get('analysis_window', 'N/A')}",
        f"<b>Generated:</b> {meta.get('generated_at', datetime.now(timezone.utc).isoformat())[:19]}",
        f"<b>Total DPRs:</b> {meta.get('total_dprs', 0)}",
        f"<b>CTG Edges:</b> {meta.get('total_edges', 0)}",
        f"<b>Decay Alerts:</b> {meta.get('total_decay_alerts', 0)}",
    ]
    for line in info:
        elements.append(Paragraph(line, body_style))
    
    elements.append(PageBreak())
    
    # ── Executive Summary ──────────────────────────────
    elements.append(Paragraph("Executive Summary", h2_style))
    
    risk_scores = data.get("risk_scores", [])
    assumptions = data.get("assumptions", [])
    backlog = data.get("remediation_backlog", [])
    dprs = data.get("dprs", [])
    
    critical_risks = [r for r in risk_scores if r.get("composite_risk", 0) >= 70]
    active_decay = [a for a in assumptions if a.get("already_decaying")]
    p0_items = [b for b in backlog if b.get("priority") == "P0"]
    
    repo_name = meta.get('repository', 'the analyzed')
    summary = (
        f"This report analyzes {len(dprs)} Decision Provenance Records (DPRs) across the {repo_name} codebase. "
        f"<b>{len(critical_risks)} DPRs</b> have critical risk scores (>=70), "
        f"<b>{len(active_decay)} assumptions</b> are actively decaying, and "
        f"<b>{len(p0_items)} items</b> require immediate remediation (P0)."
    )
    elements.append(Paragraph(summary, body_style))
    elements.append(Spacer(1, 12))
    
    # ── Risk Scores Table ──────────────────────────────
    elements.append(Paragraph("Risk Scores — Top 10", h2_style))
    
    table_data = [["DPR", "Title", "Component", "Risk", "Blast", "Decay", "Active?"]]
    for r in risk_scores[:10]:
        table_data.append([
            r["dpr_id"], r["title"][:30], r["component"],
            f"{r['composite_risk']:.0f}", r.get("blast_radius_score", ""), r.get("decay_risk_score", ""),
            "YES" if r.get("active_decay") else "no"
        ])
    
    t = Table(table_data, colWidths=[50, 130, 70, 40, 40, 40, 40])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (3,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ddd')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))
    
    # ── Decay Alerts ───────────────────────────────────
    elements.append(Paragraph("Active Decay Alerts", h2_style))
    
    for alert in assumptions:
        status = "DECAYING" if alert.get("already_decaying") else "MONITORING"
        color = '#e63946' if alert.get("already_decaying") else '#f4a261'
        elements.append(Paragraph(
            f'<font color="{color}"><b>[{status}]</b></font> '
            f'<b>{alert["dpr_id"]}</b>: {alert["assumption"][:80]}',
            body_style
        ))
        elements.append(Paragraph(f'&nbsp;&nbsp;&nbsp;Evidence: {alert.get("decay_evidence", "N/A")[:120]}', small_style))
        elements.append(Spacer(1, 4))
    
    elements.append(PageBreak())
    
    # ── Remediation Backlog ────────────────────────────
    elements.append(Paragraph("Remediation Backlog", h2_style))
    
    for item in backlog:
        pcolor = {"P0": "#e63946", "P1": "#f4a261", "P2": "#2a9d8f"}[item["priority"]]
        elements.append(Paragraph(
            f'<font color="{pcolor}"><b>[{item["priority"]}]</b></font> '
            f'<b>{item["dpr_id"]}</b>: {item["title"]} — Risk: {item["risk_score"]:.0f}',
            body_style
        ))
        for action in item.get("actions", []):
            elements.append(Paragraph(f'&nbsp;&nbsp;&nbsp;• {action}', small_style))
        elements.append(Spacer(1, 4))
    
    # ── Knowledge Concentration ────────────────────────
    kc = data.get("knowledge_concentration", {})
    spof = kc.get("spof_alerts", [])
    if spof:
        elements.append(PageBreak())
        elements.append(Paragraph("Knowledge Concentration — SPOF Alerts", h2_style))
        for alert in spof:
            elements.append(Paragraph(
                f'<b>{alert["author"]}</b> → {alert["dpr_id"]}: {alert["dpr_title"]} '
                f'({alert["ownership_pct"]}% ownership, {alert["blast_radius"]} blast radius)',
                body_style
            ))
            elements.append(Paragraph(f'&nbsp;&nbsp;&nbsp;{alert["recommendation"]}', small_style))
            elements.append(Spacer(1, 4))
    
    # ── Counterfactual Traces ──────────────────────────
    cf = data.get("counterfactual_traces", [])
    if cf:
        elements.append(PageBreak())
        elements.append(Paragraph("Counterfactual Simulation Summary", h2_style))
        for trace in cf:
            risk = trace.get("risk", {})
            rlevel = risk.get("level", "unknown")
            rcolor = {"extreme":"#e63946","high":"#f4a261","medium":"#e9c46a","low":"#2a9d8f"}.get(rlevel, "#666")
            elements.append(Paragraph(
                f'<font color="{rcolor}"><b>[{rlevel.upper()}]</b></font> '
                f'{trace.get("question", "")}',
                body_style
            ))
            elements.append(Paragraph(
                f'&nbsp;&nbsp;&nbsp;Affected: {trace.get("affected_count", 0)} DPRs across {len(trace.get("affected_components", []))} components',
                small_style
            ))
            elements.append(Spacer(1, 4))
    
    # ── Footer ─────────────────────────────────────────
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor('#ccc')))
    elements.append(Paragraph("Generated by Nexus Causal Intelligence Platform — Built on IBM Bob IDE", small_style))
    
    # Build PDF
    doc.build(elements)
    print(f"\n💾 PDF saved to: {pdf_path}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    print("✅ Risk report PDF generated")
    return str(pdf_path)

def main():
    data = load_nexus_data()
    build_pdf(data)

if __name__ == "__main__": main()
