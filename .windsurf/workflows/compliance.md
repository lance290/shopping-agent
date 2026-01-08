---
allowed-tools: "*"
description: Map compliance requirements to controls and enforcement
---
allowed-tools: "*"

1. Confirm the compliance posture for the branch (CASA level, HIPAA, SOC2, GDPR, PII flags).
2. Run the `/compliance` macro; it must emit the `# cfoi.compliance.v1` YAML block detailing Profile, Controls, and Enforcement.
3. Review the controls to ensure they align with Pulumi policies (CMEK, VPC SC, restricted egress, WAF, SIEM, synthetic data).
4. Share the block with the infra/compliance stakeholders or embed it in the PR for traceability.
5. If compliance assumptions change, rerun this workflow to refresh the YAML block.
