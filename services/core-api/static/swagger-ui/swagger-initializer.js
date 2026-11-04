// ClearTrace bootstrap for the vendored Swagger UI bundle. Kept in a file, not an
// inline script, so /api/v1/docs can run under script-src 'self' only.
window.addEventListener("load", function () {
  window.ui = SwaggerUIBundle({
    url: "/api/v1/openapi.json",
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis],
  });
});
