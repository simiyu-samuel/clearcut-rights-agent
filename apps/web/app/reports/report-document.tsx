"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useMemo, useState } from "react";
import type { ClearanceReport, Project } from "@/lib/types";

type SummaryRow = { asset: string; category: string; status: string; risk: string; confidence: string; evidence: number };
type DecisionRow = { asset: string; decision: string; actor: string; recorded: string; note: string };
type PermissionRow = { asset: string; status: string; recipient: string; due: string; subject: string };
type EvidenceItem = { title: string; url: string; excerpt: string };
type ReportDetail = { name: string; category: string; scene: string; context: string; status: string; risk: string; confidence: string; summary: string; recommendation: string; reasonCodes: string[]; evidence: EvidenceItem[] };
type ParsedReport = { title: string; metadata: Record<string, string>; notice: string; summaryRows: SummaryRow[]; details: ReportDetail[]; decisions: DecisionRow[]; permissions: PermissionRow[] };

function clean(value: string) {
  return value.replaceAll("`", "").replaceAll("**", "").trim();
}

function tableCells(line: string) {
  return line.replace(/^\||\|$/g, "").split("|").map((cell) => clean(cell));
}

function parseReport(markdown: string): ParsedReport {
  const lines = markdown.split(/\r?\n/);
  const parsed: ParsedReport = {
    title: "Clearance report",
    metadata: {},
    notice: "ClearCut provides research and workflow support. This report is not legal advice and does not declare any asset legally cleared.",
    summaryRows: [],
    details: [],
    decisions: [],
    permissions: [],
  };
  let inSummaryTable = false;
  let inDetails = false;
  let inDecisionLog = false;
  let inPermissionWork = false;
  let current: ReportDetail | null = null;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (line.startsWith("# ")) {
      parsed.title = clean(line.slice(2)).replace(/^ClearCut clearance report\s*[—-]\s*/i, "");
      continue;
    }
    if (!inSummaryTable && !inDetails && line.startsWith("- ")) {
      const metadata = line.slice(2).match(/^([^:]+):\s*(.*)$/);
      if (metadata) parsed.metadata[metadata[1].trim().toLowerCase()] = clean(metadata[2]);
      continue;
    }
    if (line.startsWith("> ")) {
      parsed.notice = clean(line.slice(2));
      continue;
    }
    if (line === "## Asset summary") {
      inSummaryTable = true;
      inDecisionLog = false;
      inPermissionWork = false;
      continue;
    }
    if (line === "## Detailed review") {
      inSummaryTable = false;
      inDetails = true;
      inDecisionLog = false;
      inPermissionWork = false;
      continue;
    }
    if (line === "## Decision log") {
      inSummaryTable = false;
      inDetails = false;
      inDecisionLog = true;
      inPermissionWork = false;
      continue;
    }
    if (line === "## Permission work") {
      inSummaryTable = false;
      inDetails = false;
      inDecisionLog = false;
      inPermissionWork = true;
      continue;
    }
    if (line === "## Method and limitations") {
      inDecisionLog = false;
      inPermissionWork = false;
      continue;
    }
    if (inSummaryTable && line.startsWith("|")) {
      if (line.includes("| Asset |")) {
        index += 1;
        continue;
      }
      const cells = tableCells(line);
      if (cells.length >= 6 && cells[0] && !cells[0].startsWith("---")) {
        parsed.summaryRows.push({ asset: cells[0], category: cells[1], status: cells[2] || "—", risk: cells[3] || "—", confidence: cells[4] || "—", evidence: Number.parseInt(cells[5], 10) || 0 });
      }
      continue;
    }
    if (inDecisionLog && line.startsWith("|")) {
      if (line.includes("| Asset | Decision |")) {
        index += 1;
        continue;
      }
      const cells = tableCells(line);
      if (cells.length >= 5 && cells[0] && !cells[0].startsWith("---")) {
        parsed.decisions.push({ asset: cells[0], decision: cells[1], actor: cells[2], recorded: cells[3], note: cells[4] });
      }
      continue;
    }
    if (inPermissionWork && line.startsWith("|")) {
      if (line.includes("| Asset | Status |")) {
        index += 1;
        continue;
      }
      const cells = tableCells(line);
      if (cells.length >= 5 && cells[0] && !cells[0].startsWith("---")) {
        parsed.permissions.push({ asset: cells[0], status: cells[1], recipient: cells[2], due: cells[3], subject: cells[4] });
      }
      continue;
    }
    const nextMeaningfulLine = lines.slice(index + 1).find((candidate) => candidate.trim().length > 0)?.trim() ?? "";
    if (inDetails && line.startsWith("### ") && nextMeaningfulLine.startsWith("- Category:")) {
      if (current) parsed.details.push(current);
      current = { name: clean(line.slice(4)), category: "", scene: "", context: "", status: "—", risk: "—", confidence: "—", summary: "", recommendation: "", reasonCodes: [], evidence: [] };
      continue;
    }
    if (!current) continue;
    if (line.startsWith("- Category:")) current.category = clean(line.slice(11));
    else if (line.startsWith("- Scene:")) current.scene = clean(line.slice(8));
    else if (line.startsWith("- Context:")) current.context = clean(line.slice(10));
    else if (line.startsWith("- Current asset status:")) current.status = clean(line.slice(23));
    else if (line.startsWith("- Clearance card status:")) current.status = clean(line.slice(24));
    else if (line.startsWith("- Risk score:")) current.risk = clean(line.slice(13));
    else if (line.startsWith("- Confidence:")) current.confidence = clean(line.slice(13));
    else if (line.startsWith("- Summary:")) current.summary = clean(line.slice(10));
    else if (line.startsWith("- Recommended next action:")) current.recommendation = clean(line.slice(27));
    else if (line.startsWith("- Reason codes:")) current.reasonCodes = clean(line.slice(15)).split(",").map((code) => code.trim()).filter(Boolean);
    else if (line.startsWith("- [")) {
      const source = line.match(/^- \[([^\]]+)\]\(([^)]+)\)\s+—\s+(.*)$/);
      if (source) current.evidence.push({ title: source[1], url: source[2], excerpt: source[3] });
    }
  }
  if (current) parsed.details.push(current);
  return parsed;
}

function label(value: string) {
  return value.replaceAll("_", " ");
}

function tone(value: string) {
  const normalized = value.toLowerCase();
  if (["approved", "complete", "likely_clear", "approved_for_delivery"].some((item) => normalized.includes(item))) return "good";
  if (["escalated", "rejected", "blocked", "high_risk"].some((item) => normalized.includes(item))) return "critical";
  return "attention";
}

function numericRisk(value: string) {
  const match = value.match(/\d+/);
  return match ? Number.parseInt(match[0], 10) : 0;
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export function ReportDocument({ projectId, project, report, reports = [report] }: { projectId: string; project: Project; report: ClearanceReport; reports?: ClearanceReport[] }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedReportId, setSelectedReportId] = useState(report.id);
  const currentReport = reports.find((item) => item.id === selectedReportId) ?? report;
  const parsed = useMemo(() => parseReport(currentReport.content_markdown), [currentReport.content_markdown]);
  const total = parsed.summaryRows.length;
  const reviewed = parsed.summaryRows.filter((row) => row.risk !== "—" || row.confidence !== "—").length;
  const attention = parsed.summaryRows.filter((row) => row.status === "—" || !["approved", "complete"].includes(row.status)).length;
  const highRisk = parsed.summaryRows.filter((row) => numericRisk(row.risk) >= 70).length;
  const evidenceCoverage = total ? Math.round((parsed.summaryRows.filter((row) => row.evidence > 0).length / total) * 100) : 0;
  const researchNeededStatuses = new Set(["needs_more_research", "needs_review", "research_needed", "—"]);
  const statusCounts = [
    { label: "Needs review", value: parsed.summaryRows.filter((row) => row.status === "pending_review").length, className: "attention" },
    { label: "Needs research", value: parsed.summaryRows.filter((row) => researchNeededStatuses.has(row.status)).length, className: "neutral" },
    { label: "Escalated", value: parsed.summaryRows.filter((row) => row.status === "escalated" || row.status === "rejected").length, className: "critical" },
    { label: "Approved", value: parsed.summaryRows.filter((row) => row.status === "approved").length, className: "good" },
  ];

  function downloadMarkdown() {
    const url = URL.createObjectURL(new Blob([currentReport.content_markdown], { type: "text/markdown" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `clearcut-${projectId}-report.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function downloadPdf() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/v1/projects/${projectId}/reports/${currentReport.id}/pdf`);
      if (!response.ok) throw new Error("Unable to download the PDF report.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `clearcut-${projectId}-report.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage("PDF downloaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to download the PDF report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="report-viewer panel">
      <div className="panel-header report-toolbar"><div><h2>Clearance report</h2><span>Version {currentReport.version_number} · Snapshot generated {displayDate(currentReport.created_at)}</span></div><div className="report-downloads">{reports.length > 1 ? <label className="report-version"><span>Version</span><select aria-label="Select report version" onChange={(event) => setSelectedReportId(event.target.value)} value={selectedReportId}>{reports.map((item) => <option key={item.id} value={item.id}>v{item.version_number} · {displayDate(item.created_at)}</option>)}</select></label> : null}<button className="secondary-button" onClick={() => window.print()} type="button">Print</button><button className="secondary-button" onClick={downloadMarkdown} type="button">Download Markdown</button><button className="primary-button" disabled={busy} onClick={() => void downloadPdf()} type="button">{busy ? "Preparing PDF…" : "Download PDF"}</button></div></div>
      {message ? <div className="report-message" role="status">{message}</div> : null}
      <div className="report-paper">
        <header className="report-cover"><div className="report-cover-brand"><span className="brand-mark">C</span><div><strong>ClearCut</strong><small>Rights intelligence</small></div></div><span className="report-cover-kicker">Evidence-backed clearance report</span><h1>{parsed.title}</h1><p>Production rights review prepared for human decision-making and distribution readiness.</p><div className="report-cover-meta"><div><span>Project type</span><strong>{project.project_type}</strong></div><div><span>Territories</span><strong>{project.territories.join(" · ") || "Not set"}</strong></div><div><span>Distribution</span><strong>{project.distribution_modes.join(" · ") || "Not set"}</strong></div><div><span>Generated</span><strong>{displayDate(currentReport.created_at)}</strong></div></div><div className="report-cover-footer"><span>Report v{currentReport.version_number} · {currentReport.id.slice(0, 8)}</span><span>{currentReport.policy_version ?? "Policy snapshot"} · Human review required</span></div></header>
        <div className="report-notice"><strong>Important boundary</strong><p>{parsed.notice}</p></div>
        <section className="report-section"><div className="report-section-heading"><span>01</span><div><span>Executive summary</span><h2>{attention ? "Action is still required" : "Ready for delivery review"}</h2></div></div><div className="report-kpi-grid"><div><span>Assets</span><strong>{total}</strong><small>in this snapshot</small></div><div className={attention ? "attention" : "good"}><span>Need attention</span><strong>{attention}</strong><small>{highRisk} high-risk signals</small></div><div className="good"><span>Evidence coverage</span><strong>{evidenceCoverage}%</strong><small>{reviewed} assets with cards</small></div><div><span>Report state</span><strong>{project.status === "complete" ? "Ready" : "Review"}</strong><small>producer decision required</small></div></div><p className="report-lead">This snapshot consolidates extracted rights-bearing assets, research evidence, model recommendations, and the current human-review boundary. Use the asset register to prioritize unresolved issues before delivery.</p></section>
        <section className="report-section"><div className="report-section-heading"><span>02</span><div><span>Risk overview</span><h2>Decision distribution</h2></div></div><div className="report-risk-grid">{statusCounts.map((item) => <div className={item.className} key={item.label}><strong>{item.value}</strong><span>{item.label}</span></div>)}</div></section>
        <section className="report-section"><div className="report-section-heading"><span>03</span><div><span>Asset register</span><h2>Every signal in scope</h2></div></div><div className="report-table-wrap"><table className="report-table"><thead><tr><th>Asset</th><th>Category</th><th>Status</th><th>Risk</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody>{parsed.summaryRows.map((row) => <tr key={`${row.asset}-${row.category}`}><td><strong>{row.asset}</strong></td><td>{label(row.category)}</td><td><span className={`report-pill ${tone(row.status)}`}>{label(row.status)}</span></td><td className={tone(row.risk)}>{row.risk}</td><td>{row.confidence}</td><td>{row.evidence} sources</td></tr>)}</tbody></table></div>{!parsed.summaryRows.length ? <div className="report-empty">No assets were included in this report snapshot.</div> : null}</section>
        <section className="report-section"><div className="report-section-heading"><span>04</span><div><span>Detailed review</span><h2>Evidence and recommended action</h2></div></div><div className="report-detail-list">{parsed.details.map((detail) => <article className="report-detail" key={detail.name}><div className="report-detail-header"><div><span>{label(detail.category) || "Asset"}{detail.scene ? ` · Scene ${detail.scene}` : ""}</span><h3>{detail.name}</h3></div><span className={`report-pill ${tone(detail.status)}`}>{label(detail.status)}</span></div><div className="report-detail-context"><span>Source context</span><p>{detail.context || "Context not recorded."}</p></div>{detail.summary || detail.recommendation ? <div className="report-detail-grid"><div><span>Assessment</span><p>{detail.summary || "No assessment recorded."}</p><div className="report-score-line"><strong>{detail.risk}</strong><small>risk</small><strong>{detail.confidence}</strong><small>confidence</small></div></div><div className="report-recommendation"><span>Recommended next action</span><p>{detail.recommendation || "Review the asset and determine the next clearance action."}</p></div></div> : null}<div className="report-detail-footer"><div><span>Evidence</span>{detail.evidence.length ? <div className="report-source-list">{detail.evidence.map((source) => <a href={source.url} key={source.url} rel="noreferrer" target="_blank"><strong>{source.title}</strong><small>{source.excerpt}</small></a>)}</div> : <small>No source records returned.</small>}</div>{detail.reasonCodes.length ? <div><span>Reason codes</span><div className="report-reasons">{detail.reasonCodes.map((code) => <em key={code}>{label(code)}</em>)}</div></div> : null}</div></article>)}</div></section>
        <section className="report-section"><div className="report-section-heading"><span>05</span><div><span>Permission work</span><h2>Requests and response state</h2></div></div>{parsed.permissions.length ? <div className="report-table-wrap"><table className="report-table"><thead><tr><th>Asset</th><th>Status</th><th>Recipient</th><th>Due</th><th>Subject</th></tr></thead><tbody>{parsed.permissions.map((permission, index) => <tr key={`${permission.asset}-${index}`}><td><strong>{permission.asset}</strong></td><td><span className={`report-pill ${tone(permission.status)}`}>{label(permission.status)}</span></td><td>{permission.recipient}</td><td>{permission.due}</td><td>{permission.subject}</td></tr>)}</tbody></table></div> : <div className="report-empty">No permission requests have been drafted in this snapshot.</div>}</section>
        <section className="report-section"><div className="report-section-heading"><span>06</span><div><span>Decision log</span><h2>Human accountability</h2></div></div>{parsed.decisions.length ? <div className="report-table-wrap"><table className="report-table"><thead><tr><th>Asset</th><th>Decision</th><th>Actor</th><th>Recorded</th><th>Note</th></tr></thead><tbody>{parsed.decisions.map((decision, index) => <tr key={`${decision.asset}-${index}`}><td><strong>{decision.asset}</strong></td><td><span className={`report-pill ${tone(decision.decision)}`}>{label(decision.decision)}</span></td><td>{decision.actor}</td><td>{decision.recorded}</td><td>{decision.note}</td></tr>)}</tbody></table></div> : <div className="report-empty">No human decisions have been recorded in this snapshot.</div>}</section>
        <section className="report-section report-method"><div className="report-section-heading"><span>07</span><div><span>Method and limitations</span><h2>What this snapshot means</h2></div></div><div className="report-method-grid"><div><span>Evidence basis</span><strong>Stored source records and excerpts</strong><p>Sources are retained with their retrieval metadata for traceability.</p></div><div><span>Decision boundary</span><strong>Human approval remains required</strong><p>Recommendations support workflow; they do not grant legal rights.</p></div><div><span>Next review</span><strong>Before distribution</strong><p>Recheck unresolved or time-sensitive evidence before delivery.</p></div></div></section>
      </div>
    </section>
  );
}
