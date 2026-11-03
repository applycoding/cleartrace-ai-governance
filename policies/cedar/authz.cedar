permit (
  principal,
  action,
  resource
) when {
  context has roles &&
  (
    (action == Action::"health") ||
    (action == Action::"view_dashboard" && context.roles.contains("read_only_viewer")) ||
    (action == Action::"view_system" && (
      context.roles.contains("read_only_viewer") ||
      context.roles.contains("system_owner") ||
      context.roles.contains("assessor") ||
      context.roles.contains("oversight_reviewer") ||
      context.roles.contains("auditor") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"create_system" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"update_system" && (
      context.roles.contains("system_owner") ||
      context.roles.contains("tenant_admin")
    )) ||
    (action == Action::"admin" && context.roles.contains("tenant_admin"))
  )
};
