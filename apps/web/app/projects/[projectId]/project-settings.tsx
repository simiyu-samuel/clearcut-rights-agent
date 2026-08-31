"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useState } from "react";
import type { Project } from "@/lib/types";
import { ProjectOptionPicker } from "../project-option-picker";
import {
  createProjectOption,
  labelsFor,
  loadProjectOptions,
  type ProjectOption,
  type ProjectOptionType,
} from "../project-options";

export function ProjectSettings({ project, onSaved }: { project: Project; onSaved: (project: Project) => void }) {
  const { organizationRole } = useAuth();
  const canEdit = ["admin", "producer", "coordinator"].includes(organizationRole ?? "");
  const [title, setTitle] = useState(project.title);
  const [projectType, setProjectType] = useState(project.project_type);
  const [territories, setTerritories] = useState(project.territories);
  const [distributionModes, setDistributionModes] = useState(project.distribution_modes);
  const [options, setOptions] = useState<ProjectOption[]>([]);
  const [targetReleaseAt, setTargetReleaseAt] = useState(project.target_release_at?.slice(0, 10) ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const canCreateOptions = canEdit && ["admin", "producer"].includes(organizationRole ?? "");

  useEffect(() => {
    let mounted = true;
    void loadProjectOptions()
      .then((loadedOptions) => { if (mounted) setOptions(loadedOptions); })
      .catch(() => { /* Built-in options remain available when the catalog is unavailable. */ });
    return () => { mounted = false; };
  }, []);

  async function addWorkspaceOption(optionType: ProjectOptionType, label: string) {
    const created = await createProjectOption(optionType, label);
    setOptions((current) => [...current, created]);
    return created.label;
  }

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
          territories,
          distribution_modes: distributionModes,
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
      <ProjectOptionPicker
        canCreate={canCreateOptions}
        disabled={!canEdit}
        onChange={(values) => setProjectType(values[0] ?? "")}
        onCreateOption={(label) => addWorkspaceOption("project_type", label)}
        options={labelsFor(options, "project_type", projectType ? [projectType] : [])}
        selected={projectType ? [projectType] : []}
        label="Project type"
        placeholder="Search project types"
      />
      <ProjectOptionPicker
        canCreate={canCreateOptions}
        disabled={!canEdit}
        multiple
        onChange={setTerritories}
        onCreateOption={(label) => addWorkspaceOption("territory", label)}
        options={labelsFor(options, "territory", territories)}
        selected={territories}
        hint="Select all that apply"
        label="Territories"
        placeholder="Search territories"
      />
      <ProjectOptionPicker
        canCreate={canCreateOptions}
        disabled={!canEdit}
        multiple
        onChange={setDistributionModes}
        onCreateOption={(label) => addWorkspaceOption("distribution_mode", label)}
        options={labelsFor(options, "distribution_mode", distributionModes)}
        selected={distributionModes}
        hint="Select all that apply"
        label="Distribution modes"
        placeholder="Search distribution modes"
      />
      <label className="form-field"><span>Release target <small>Used for delivery planning</small></span><input disabled={!canEdit} type="date" value={targetReleaseAt} onChange={(event) => setTargetReleaseAt(event.target.value)} /></label>
    </div>
    {message ? <div className={message === "Project settings saved." ? "form-success" : "form-message"} role="status">{message}</div> : null}
    <div className="form-actions"><button className="primary-button" disabled={!canEdit || busy || !title.trim() || !projectType.trim()} onClick={() => void save()} type="button">{busy ? "Saving…" : "Save project settings"}</button></div>
    <div className="disclaimer"><strong>{canEdit ? "Project status is workflow-derived." : "Your role has view-only project settings."}</strong><br />{canEdit ? "ClearCut updates status from source, research, and human review state. Editing metadata is recorded in the activity log." : "Ask an admin, producer, or coordinator to update the project context."}</div>
  </section>;
}
