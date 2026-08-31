"use client";

import { authorizedFetch as fetch } from "@/lib/api-client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function NewProjectForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [projectType, setProjectType] = useState("Feature film");
  const [territories, setTerritories] = useState("Kenya, United Kingdom");
  const [distributionModes, setDistributionModes] = useState("Streaming");
  const [targetReleaseAt, setTargetReleaseAt] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

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
          territories: territories.split(",").map((value) => value.trim()).filter(Boolean),
          distribution_modes: distributionModes.split(",").map((value) => value.trim()).filter(Boolean),
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
        <label className="form-field"><span>Project type</span><input required value={projectType} onChange={(event) => setProjectType(event.target.value)} /></label>
        <label className="form-field"><span>Territories</span><input value={territories} onChange={(event) => setTerritories(event.target.value)} /></label>
        <label className="form-field"><span>Distribution modes</span><input value={distributionModes} onChange={(event) => setDistributionModes(event.target.value)} /></label>
        <label className="form-field"><span>Target release date <small>Optional</small></span><input type="date" value={targetReleaseAt} onChange={(event) => setTargetReleaseAt(event.target.value)} /></label>
        {message ? <div className="form-message" role="status">{message}</div> : null}
        <div className="form-actions"><button className="primary-button" disabled={busy} type="submit">{busy ? "Creating…" : "Create project"}</button></div>
      </div>
    </form>
  );
}
