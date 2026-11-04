window.addEventListener("load", function () {
  window.ui = SwaggerUIBundle({
    url: "/api/v1/openapi.json",
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    oauth2RedirectUrl: window.location.origin + "/api/v1/docs/oauth2-redirect",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
  });
});
