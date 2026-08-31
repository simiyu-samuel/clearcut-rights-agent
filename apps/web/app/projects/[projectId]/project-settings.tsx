"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import type { Project } from "@/lib/types";

export function ProjectSettings({ project, onSaved }: { project: Project; onSaved: (project: Project) => void }) {
  const { organizationRole } = useAuth();
  const canEdit = ["admin", "producer", "coordinator"].includes(organizationRole ?? "");
  const [title, setTitle] = useState(project.title);
  const [projectType, setProjectType] = useState(project.project_type);
  const [territories, setTerritories] = useState(project.territories.join(", "));
  const [distributionModes, setDistributionModes] = useState(project.distribution_modes.join(", "));
  const [targetReleaseAt, setTargetReleaseAt] = useState(project.target_release_at?.slice(0, 10) ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/v1/projects/${project.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          project_type: projectType.trim(),
          territories: territories.split(",").map((value) => value.trim()).filter(Boolean),
          distribution_modes: distributionModes.split(",").map((value) => value.trim()).filter(Boolean),
          target_release_at: targetReleaseAt ? `${targetReleaseAt}T23:59:59Z` : null,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to save project settings.");
      }
      onSaved(await response.json() as Project);
      setMessage("Project settings saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save project settings.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel project-settings-panel">
    <div className="panel-header"><div><h2>Project configuration</h2><span>Production context used by clearance workflows</span></div><span className={`status-chip ${project.status}`}>{project.status.replaceAll("_", " ")}</span></div>
    <div className="project-settings-form">
      <label className="form-field"><span>Project title</span><input disabled={!canEdit} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label className="form-field"><span>Project type</span><input disabled={!canEdit} value={projectType} onChange={(event) => setProjectType(event.target.value)} /></label>
      <label className="form-field"><span>Territories <small>Comma separated</small></span><input disabled={!canEdit} value={territories} onChange={(event) => setTerritories(event.target.value)} /></label>
      <label className="form-field"><span>Distribution modes <small>Comma separated</small></span><input disabled={!canEdit} value={distributionModes} onChange={(event) => setDistributionModes(event.target.value)} /></label>
      <label className="form-field"><span>Release target <small>Used for delivery planning</small></span><input disabled={!canEdit} type="date" value={targetReleaseAt} onChange={(event) => setTargetReleaseAt(event.target.value)} /></label>
    </div>
    {message ? <div className={message === "Project settings saved." ? "form-success" : "form-message"} role="status">{message}</div> : null}
    <div className="form-actions"><button className="primary-button" disabled={!canEdit || busy || !title.trim() || !projectType.trim()} onClick={() => void save()} type="button">{busy ? "Saving…" : "Save project settings"}</button></div>
    <div className="disclaimer"><strong>{canEdit ? "Project status is workflow-derived." : "Your role has view-only project settings."}</strong><br />{canEdit ? "ClearCut updates status from source, research, and human review state. Editing metadata is recorded in the activity log." : "Ask an admin, producer, or coordinator to update the project context."}</div>
  </section>;
}
