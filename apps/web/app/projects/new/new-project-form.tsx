"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ProjectOptionPicker } from "../project-option-picker";
import {
  createProjectOption,
  labelsFor,
  loadProjectOptions,
  type ProjectOption,
  type ProjectOptionType,
} from "../project-options";

export function NewProjectForm() {
  const router = useRouter();
  const { organizationRole } = useAuth();
  const [title, setTitle] = useState("");
  const [projectType, setProjectType] = useState("Feature film");
  const [territories, setTerritories] = useState(["Kenya", "United Kingdom"]);
  const [distributionModes, setDistributionModes] = useState(["Streaming"]);
  const [options, setOptions] = useState<ProjectOption[]>([]);
  const [targetReleaseAt, setTargetReleaseAt] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const canCreateOptions = ["admin", "producer"].includes(organizationRole ?? "");

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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/v1/projects`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-organization-id": "demo-org" },
        body: JSON.stringify({
          title,
          project_type: projectType,
          territories,
          distribution_modes: distributionModes,
          target_release_at: targetReleaseAt ? `${targetReleaseAt}T23:59:59Z` : null,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Unable to create project.");
      }
      const project = await response.json();
      router.push(`/projects/${project.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create project.");
      setBusy(false);
    }
  }

  return (
    <form className="project-form panel" onSubmit={submit}>
      <div className="panel-header"><div><h2>Project details</h2><span>Stored in the ClearCut workspace</span></div></div>
      <div className="project-form-body">
        <label className="form-field"><span>Project title</span><input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. The Last Signal" /></label>
        <ProjectOptionPicker
          canCreate={canCreateOptions}
          onChange={(values) => setProjectType(values[0] ?? "")}
          onCreateOption={(label) => addWorkspaceOption("project_type", label)}
          options={labelsFor(options, "project_type", projectType ? [projectType] : [])}
          selected={projectType ? [projectType] : []}
          label="Project type"
          placeholder="Search project types"
        />
        <ProjectOptionPicker
          canCreate={canCreateOptions}
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
          multiple
          onChange={setDistributionModes}
          onCreateOption={(label) => addWorkspaceOption("distribution_mode", label)}
          options={labelsFor(options, "distribution_mode", distributionModes)}
          selected={distributionModes}
          hint="Select all that apply"
          label="Distribution modes"
          placeholder="Search distribution modes"
        />
        <label className="form-field"><span>Target release date <small>Optional</small></span><input type="date" value={targetReleaseAt} onChange={(event) => setTargetReleaseAt(event.target.value)} /></label>
        {message ? <div className="form-message" role="status">{message}</div> : null}
        <div className="form-actions"><button className="primary-button" disabled={busy} type="submit">{busy ? "Creating…" : "Create project"}</button></div>
      </div>
    </form>
  );
}
