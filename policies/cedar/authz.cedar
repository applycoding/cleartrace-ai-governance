permit (
  principal,
  action,
  resource
) when {
  context has roles &&
  (
    (action == Action::"health") ||
    (action == Action::"view_dashboard" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("policy_steward")
    )) ||
    (action == Action::"view_system" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("policy_steward") ||
      context.roles.contains("approver")
    )) ||
    (action == Action::"create_system" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"update_system" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"run_assessment" && (
      context.roles.contains("assessor") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"upload_evidence" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("approver") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("auditor")
    )) ||
    (action == Action::"view_evidence" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("approver")
    )) ||
    (action == Action::"review_finding" && context.roles.contains("oversight_reviewer")) ||
    (action == Action::"read_audit" && (
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("platform_operator")
    )) ||
    (action == Action::"verify_audit" && (
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("platform_operator")
    )) ||
    (action == Action::"view_data_policy" && (
      context.roles.contains("tenant_admin") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("auditor") ||
      context.roles.contains("read_only_viewer")
    )) ||
    (action == Action::"mutate_data_policy" && context.roles.contains("tenant_admin")) ||
    (action == Action::"export_interop" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"manage_connectors" && (
      context.roles.contains("tenant_admin") ||
      context.roles.contains("system_owner")
    )) ||
    (action == Action::"run_connector" && (
      context.roles.contains("tenant_admin") ||
      context.roles.contains("system_owner")
    )) ||
    (action == Action::"register_import" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"view_policy_watch" && (
      context.roles.contains("policy_steward") ||
      context.roles.contains("tenant_admin") ||
      context.roles.contains("read_only_viewer")
    )) ||
    (action == Action::"promote_policy_diff" && (
      context.roles.contains("policy_steward") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"manage_risk_metrics" && (
      context.roles.contains("assessor") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"post_observations" && (
      context.roles.contains("assessor") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"view_notifications" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"manage_webhooks" && context.roles.contains("tenant_admin")) ||
    (action == Action::"create_report" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"aia_score" && (
      context.roles.contains("assessor") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"admin" && context.roles.contains("tenant_admin"))
  )
};
